# Written by Brendan O'Connor, brenocon@gmail.com, www.anyall.org
#  * Originally written Aug. 2005
#  * Posted to gist.github.com/16173 on Oct. 2008

#   Copyright (c) 2003-2006 Open Source Applications Foundation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import random
import re
import types

"""This file has been *heavily* modified to remove the use of global variables, implement
a logging class instead of relying on sys.stdout, remove the function log decorator, remove
the module log decorator, allow color changing on any log call,
allow indentation level changing on any log call, and PEP-8 formatting.
Copyright (C) 2013 Ben Gelb
"""


BLACK = "\033[0;30m"
BLUE = "\033[0;34m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
RED = "\033[0;31m"
PURPLE = "\033[0;35m"
BROWN = "\033[0;33m"
GRAY = "\033[0;37m"
BOLDGRAY = "\033[1;30m"
BOLDBLUE = "\033[1;34m"
BOLDGREEN = "\033[1;32m"
BOLDCYAN = "\033[1;36m"
BOLDRED = "\033[1;31m"
BOLDPURPLE = "\033[1;35m"
BOLDYELLOW = "\033[1;33m"
WHITE = "\033[1;37m"
NORMAL = "\033[0m"


class Logger(object):
    def __init__(self, indent_string=' ', indent_level=0, *args, **kwargs):
        self.__log = None
        self.indent_string = indent_string
        self.indent_level = indent_level

    @property
    def __logger(self):
        if not self.__log:
            FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
            self.__log = logging.getLogger(__name__)
            self.__log.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(logging.Formatter(FORMAT))
            self.__log.addHandler(handler)
        return self.__log

    def _log_levels(self, level):
        return {
            'debug': 10,
            'info': 20,
            'warning': 30,
            'critical': 40,
            'error': 50
        }.get(level, 'info')

    def update_indent_level(self, val):
        self.indent_level = val

    def log(self, message, color=None, log_level='info', indent_level=None, *args, **kwargs):
        msg_params = {
            'color': color or NORMAL,
            'indent': self.indent_string * (indent_level or self.indent_level),
            'msg': message
        }
        _message = "{color} {indent}{msg}".format(**msg_params)
        self.__logger.log(self._log_levels(log_level), _message)


def format_args(args, kwargs):
    """
    makes a nice string representation of all the arguments
    """
    allargs = []
    for item in args:
        allargs.append('%s' % str(item))

    for key, item in kwargs.items():
        allargs.append('%s=%s' % (key, str(item)))

    formattedArgs = ', '.join(allargs)

    if len(formattedArgs) > 150:
        return formattedArgs[:146] + " ..."
    return formattedArgs


def log_method(method, display_name=None):
    """use this for class or instance methods, it formats with the object out front."""
    display_name = display_name or method.__name__
    print(display_name)
    if display_name == "log":
        raise Exception("")
    def _wrapper(self, *args, **kwargs):
        arg_str = format_args(args, kwargs)
        message = "{self_str}.{cls_color}{method_display_name}{method_color} ({arg_str})".format(**{
            'self_str': str(self),
            'cls_color': BROWN,
            'method_display_name': "{} - {}".format(method.__name__, display_name),
            'method_color': NORMAL,
            'arg_str': arg_str
        })
        self.log(message)
        #self.logger_instance.update_indent_level(self.logger_instance.indent_level + 1)
        returnval = method(self, *args, **kwargs)
        #self.logger_instance.update_indent_level(self.logger_instance.indent_level - 1)
        return returnval
    return _wrapper


def log_class(cls, log_match=".*", log_no_match="asdfnomatch", display_name=None):
    display_name = display_name or "%s" % (cls.__name__)
    names_to_check = cls.__dict__.keys()
    allow = lambda s: all([
        re.match(log_match, s),
        not re.match(log_no_match, s),
        s not in ('__str__', '__repr__')
    ])
    for name in names_to_check:
        
        if not allow(name):
            continue
        # unbound methods show up as mere functions in the values of
        # cls.__dict__,so we have to go through getattr
        value = getattr(cls, name)
        #print(cls.__dict__)
        
        if isinstance(value, types.FunctionType):
            ####if value.im_self is None:
                ####print(name, value, type(value))
            setattr(cls, name, log_method(value, display_name=display_name))

        if isinstance(value, types.MethodType):
            print(name, value)
            # a normal instance method
            if value.im_self is None:
                setattr(cls, name, log_method(value, display_name=display_name))

            # check for cls method. class & static method are more complex.
            elif value.im_self == cls:
                _display_name = "%s.%s" % (cls.__name__, value.__name__)
                w = log_method(value.im_func, display_name=_display_name)
                setattr(cls, name, classmethod(w))
            else:
                assert False
    return cls


class WorkflowStep(object):
    def __init__(self, *args, **kwargs):
        self.__logger = None

    @property
    def logger_instance(self):
        if "__logger" not in self.__dict__ or not self.__logger:
            self.__logger = Logger()
        return self.__logger

    def log(self, message, *args, **kwargs):
        self.logger_instance.log(message, *args, **kwargs)


#@log_class
#class CleanNumeric(WorkflowStep):
    ##@log_method     # just for fun
    #def clean_line(self, line, start=0, stop=3, *args, **kwargs):
        ## recursion just so we can experiment with the tracing
        ##self.log("Recursing number %s" % start, color=BOLDGREEN)
        #if start > stop:
            #return line
        #return self.randomize(line, start=start+1, stop=stop)

    #def randomize(self, line, start=None, stop=None, *args, **kwargs):
        ## recursion just so we can experiment with the tracing
        #random.shuffle(line)
        #return self.clean_line(line, start=start, stop=stop)

#cn = CleanNumeric()
#cn.clean_line([1,2,3,4,5])
