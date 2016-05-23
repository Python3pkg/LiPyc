from tkinter import * 
import sys 

class Panel(Frame):
    def __init__(self, master, *args, **kw):
        super().__init__(master, *args, **kw)
        
    def hide(self):
        self.grid_forget()
        
    def show(self):
        self.grid()

# http://tkinter.unpythonic.net/wiki/VerticalScrolledFrame
#https://code.activestate.com/recipes/578894-mousewheel-binding-to-scrolling-area-tkinter-multi/
class ScrollingArea:  
    def __init__(self, root, factor = 2):
        
        self.activeArea = None
        
        if type(factor) == int:
            self.factor = factor
        else:
            raise Exception("Factor must be an integer.")

        if sys.platform.startswith('linux') :
            root.bind_all('<4>', self._on_mouse_wheel,  add='+')
            root.bind_all('<5>', self._on_mouse_wheel,  add='+')
        else:
            root.bind_all("<MouseWheel>", self._on_mouse_wheel,  add='+')

    def _on_mouse_wheel(self,event):       
        if self.activeArea and self.activeArea != self:
            self.activeArea._on_mouse_wheel(event)

    def _mouse_wheel_bind(self, widget):
        self.activeArea = widget

    def _mouse_wheel_unbind(self):
        self.activeArea = None

    def build_function__on_mouse_wheel(self, widget, orient, factor = 1):
        view_command = getattr(widget, orient+'view')
        
        if sys.platform.startswith('linux'):
            def _on_mouse_wheel(event):
                if event.num == 4:
                    view_command("scroll",(-1)*factor,"units" )
                elif event.num == 5:
                    view_command("scroll",factor,"units" ) 

        elif sys.platform == 'win32' or sys.platform == 'cygwin':
            def _on_mouse_wheel(event):        
                view_command("scroll",(-1)*int((event.delta/120)*factor),"units" ) 

        elif sys.platform == 'darwin':
            def _on_mouse_wheel(event):        
                view_command("scroll",event.delta,"units" )             
        
        return _on_mouse_wheel
        

    def add_scrolling(self, scrollingArea, xscrollbar=None, yscrollbar=None):
        if yscrollbar:
            scrollingArea.configure(xscrollcommand=yscrollbar.set)
            yscrollbar['command']=scrollingArea.yview

        if xscrollbar:
            scrollingArea.configure(yscrollcommand=xscrollbar.set)
            xscrollbar['command']=scrollingArea.xview
        
        scrollingArea.bind('<Enter>',lambda event: self._mouse_wheel_bind(scrollingArea))
        scrollingArea.bind('<Leave>', lambda event: self._mouse_wheel_unbind())

        if xscrollbar and not hasattr(xscrollbar, '_on_mouse_wheel'):
            xscrollbar._on_mouse_wheel = self.build_function__on_mouse_wheel(scrollingArea,'x', self.factor)

        if yscrollbar and not hasattr(yscrollbar, '_on_mouse_wheel'):
            yscrollbar._on_mouse_wheel = self.build_function__on_mouse_wheel(scrollingArea,'y', self.factor)

        main_scrollbar = yscrollbar or xscrollbar
        
        if main_scrollbar:
            scrollingArea._on_mouse_wheel = main_scrollbar._on_mouse_wheel

        for scrollbar in (xscrollbar, yscrollbar):
            if scrollbar:
                scrollbar.bind('<Enter>', lambda event, scrollbar=scrollbar: self._mouse_wheel_bind(scrollbar) )
                scrollbar.bind('<Leave>', lambda event: self._mouse_wheel_unbind())
        
class VScrolledPanel(Panel):
    """A pure Tkinter scrollable frame that actually works!

    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling
    
    """
    def __init__(self, master, *args, **kw):
        super().__init__(master, *args, **kw)         

        # create a canvas object and a vertical scrollbar for scrolling it
        self.vscrollbar = Scrollbar(self, orient=VERTICAL)
        self.vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        self.canvas = Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=self.vscrollbar.set)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        self.vscrollbar.config(command=self.canvas.yview)

        # reset the view
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = Frame(self.canvas, bg="white",)
        interior_id = self.canvas.create_window(0, 0, window=interior,
                                           anchor=NW)

        # track changes to the canvas and frame width and sync them,    
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())

            self.canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != self.canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                self.canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != self.canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                self.canvas.itemconfigure(interior_id, width=self.canvas.winfo_width())
        self.canvas.bind('<Configure>', _configure_canvas)
        
        
        ScrollingArea(self).add_scrolling(self.canvas, yscrollbar=self.vscrollbar)
        
    def reset(self):
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
