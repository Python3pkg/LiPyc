#speed use only to select : read replicat
#nom => identifiant unique pour l'utilisateur(au sein d'un mêm parent)
import os 
from pkg_resources import resource_filename, resource_exists

max_ratio = 100 #on ne peut multiplier la proba que par 5 au plus
counter = 0
#delay_snapshot = 100#nombre d'operations entre deux snapshots
size_transaction  = 100
delay_transaction = 1.
default_replicat = 2

location_pgs_default = resource_filename("lipyc.data", "default-pgs.json")
