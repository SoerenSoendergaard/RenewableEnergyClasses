# -*- coding: utf-8 -*-
"""
Created on Fri Nov 11 17:57:05 2022

@author: soere
"""

import pypsa
import numpy as np

# Create a network with one node and open for five hours of data
# This network is expanded later in the script to contain both DK1 and DK2
network = pypsa.Network()

network.set_snapshots(range(5))

# Add a single node
network.add("Bus", "bus0")

# add a load to the node. In all 5 hours the demand is 2000MW
network.add("Load",
            "load", 
            bus="bus0", 
            p_set=[2000, 2000, 2000, 2000, 2000])

# Function used to annualize costs
def annuity(n,r):
    """Calculate the annuity factor for an asset with lifetime n years and
    discount rate of r, e.g. annuity(20,0.05)*20 = 1.6"""

    if r > 0:
        return r/(1. - 1./(1.+r)**n)
    else:
        return 1/n

# add a generator to the node.
# bus1 is dk1 and has a onshore turbine availible, with capacity factors known for the 5 hours.
# The carriers of the system is defined and their capacity factors.
network.add("Carrier", "onshorewind")
network.add("Carrier", "solar")
CF_wind = [1, 0.8, 0.5, 0.25, 0.8]
CF_solar = [0.5, 0.4, 0.3, 0.2, 0.1]

# The capital cost is annualized
capital_cost_onshorewind = annuity(30,0.07)*910000 # in €/MW
capital_cost_onshorewind = capital_cost_onshorewind*(5/8760) # for 5 weeks
capital_cost_solar = annuity(30,0.07)*425000# in €/MW
capital_cost_solar = capital_cost_solar*(5/8760)

# Add onshore wind generator to node 1
network.add("Generator",
            "onshorewind",
            bus="bus0",
            p_nom_extendable=True,
            carrier="onshorewind",
            #p_nom_max=1000, # maximum capacity can be limited due to environmental constraints
            capital_cost = capital_cost_onshorewind,
            marginal_cost = 0,
            p_max_pu = CF_wind)

# Testing
network.generators_t.p_max_pu

network.lopf(network.snapshots, 
             pyomo=False,
             solver_name='gurobi')

# Calculate price of electricity in 1 node
print(network.objective/network.loads_t.p.sum())

DK_1_el_price_1_node = network.objective/network.loads_t.p.sum()


# The installed capacitys:
DK_1_installed_capacity_1_node = network.generators.p_nom_opt

# -------------------

# Make model for DK2 called network_2
# Add Another node to the model that only has solar

network_2 = pypsa.Network()

network_2.set_snapshots(range(5))
network_2.add("Carrier", "solar")

network_2.add("Bus", "bus1")


# add a load to the node. In all 5 hours the demand is 2000MW
network_2.add("Load",
            "load2", 
            bus="bus1", 
            p_set=[2000, 2000, 2000, 2000, 2000])

network_2.add("Generator",
            "solar",
            bus="bus1",
            p_nom_extendable=True,
            carrier="solar",
            #p_nom_max=1000, # maximum capacity can be limited due to environmental constraints
            capital_cost = capital_cost_solar,
            marginal_cost = 0,
            p_max_pu = CF_solar)

network_2.lopf(network.snapshots, 
             pyomo=False,
             solver_name='gurobi')

# Calculate price of electricity in 1 node
print(network_2.objective/network_2.loads_t.p.sum())

DK_2_el_price_1_node = network_2.objective/network_2.loads_t.p.sum()

# The installed capacitys:
DK_2_installed_capacity_1_node = network_2.generators.p_nom_opt


# ----------
# Add Another node to the model of "network" that only has solar
# To make joint model

network.add("Bus", "bus1")

# add a load to the node. In all 5 hours the demand is 2000MW
network.add("Load",
            "load2", 
            bus="bus1", 
            p_set=[2000, 2000, 2000, 2000, 2000])

network.add("Generator",
            "solar",
            bus="bus1",
            p_nom_extendable=True,
            carrier="solar",
            #p_nom_max=1000, # maximum capacity can be limited due to environmental constraints
            capital_cost = capital_cost_solar,
            marginal_cost = 0,
            p_max_pu = CF_solar)



# Add a link between the nodes
capital_cost_link = annuity(30,0.07)*400# in €/MW
capital_cost_link = capital_cost_link*(5/8760)
capital_cost_link = capital_cost_link*58

network.add("Link",
             'DK1 - DK2',
             bus0="bus0",
             bus1="bus1",
             p_nom_extendable=True, # capacity is optimised
             p_min_pu=-1,
             efficiency = 1,
             marginal_cost = 0,
             length=58, # length (in km) between country a and country b
             capital_cost=capital_cost_link) # capital cost * length 

network.lopf(network.snapshots, 
             pyomo=False,
             solver_name='gurobi')

# Calculate price of electricity in 1 node
Joined_model_avg_el_price = network.objective/sum(network.loads_t.p.sum())

LinkCapacity = network.links.p_nom_opt
# The installed capacitys:
Joined_model_installed_capacity = network.generators.p_nom_opt

import matplotlib.pyplot as plt

plt.plot([4000, 4000, 4000, 4000, 4000], color='black', label='demand')
plt.plot(network.generators_t.p['onshorewind'][0:96], color='blue', label='onshore wind')
plt.plot(network.generators_t.p['solar'][0:96], color='orange', label='solar')
plt.plot(network.links_t.p0['DK1 - DK2'][0:96],color='red', label='link (positive from DK1 to DK2')
plt.xlabel("Time [Hours]")
plt.ylabel("Energy [MW]")
plt.legend(fancybox=True, shadow=True, loc='best')
plt.title('Dispatch, transfer and demand of energy')
