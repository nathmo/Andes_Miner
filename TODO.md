-> create a repo with game screen shot / doc / readme / instruction and a github action that compile a .exe, .deb and MacOS app when pushing change.
-> PAUSE HERE, from now one, each of theses point should be made into a commit so that if anything break we can revert easily.

-> add sprite for iced coffee, rename coffee to iced coffee. (use an emoji for now, export it to png)
-> add sprite for jammies ( a blue circular coin)
-> make the wage action based and not time based. (like 10 tile action = 1 iced coffee ) so the game is not time pressured.
-> make the cleaning of rubble drop a rubble entity that need to be picked up.
-> add select animation for cleaning rubble (to know which one are currently scheduled for cleaning like its done for mining).do the same for the roads when they are scheduled for construction.
-> for the excavated texture, make it differentiated based on the original tile (excavated andesite dont look the same as excavated basalte)
-> road shoudl cost rubble that need to be brought to site to be converted to road
-> need to add a medium machine to build the road without a human worker
-> Need to add a starting building that serve as a storage (so they dont just drop entity on the road in 0,0)
-> need to add a new building that allow to plan mining operation automatically ( so that we can drag and select large area to mine and once this building exist, the planning of mining and road building to reach the requested ore can be automated.)
-> need to make vehicle and worker find the shortes path timewise (aka use the road to go faster) if not done aldready. If it was done aldready, it mean we need to slow down more the rubble and make the road faster they the excavated rock.
-> vehicle of first tier can mine rock whithin 2 tile, medium one can go 3 tile, the mega machine can do 4 tile away
-> cargo vehicle have a capacity that depend of tier. small one can do only carry one item. medium can carry 3, large can carry 9 item. (and thus for the mega machine, we can keep mining/cleaning rubble and only drop the ore/rubble once fully full)
-> need to make machine of higher tier much more expensive and every machine should much slower to give an incentive to build more than one (having a processing time that make sense so that its fun and not impossible to saturate).


-> need to implement cable car, they go in straight line back to the center house, use to increase troughput of ore transporter as they can get quite slow once we are far away from center coord. come as a building pair. can only be built on road.

-> there should be an overarching goal that give a sense of direction (maybe connect the top of the world to the bottom, we can restrict the map vertically and once the minning operation work well the goal is actually to connect randomly generated village to the top / bottom of the mountains (thus encouraging laterral exploration) and in between them.) (link with the road planning building that can start doing it but it required an upgrade / mobility infrastructure planning and that get very expensive so that the game dont play itself too quick)

-> when pointing a tile, it should also give info on the item dropped on it ( is it rubble ? iron ore ? copper ore ? ...) and excavated tile will not drop anything thus should not display that they contain ore., just give the name/state (example : diorite rubbles, exavated basalt, ryholite (drop XX), )

-> there might be room for some other meterial to mine, maybe at first we also need to buy electricity but over time we can convert rubble to SIO2 and discover some lithium salt patch. from there new building allow to process them into solar panel that can be build to create energy generation and thus reduce / remove the need to buy Kwh to run the machine (cable car, furnance, crusher, electrolysis plant for lithium salt, ...)

-> maybe there is a market where we can buy and sell material we dont have (to make machine since we cant mine all the ressources from the start. for instance now vehicle require also lithium and silicon that we have to buy and we just start the game with a certain cash capital to make the first few machine (or just straight sell the rubble and raw ore for cash to buy coffee and all))

-> add a "stock market" with varying price (something that have some part of random fluctiation and some long trend that are derivated from the player production -> the more they sell rubble, the less its worth, same for other material but ensure they dont fall lower than a minimal sustainable price so taht we can always buy cofee for workers.) (maybe a new button that open the pannel with the price and also the current production trend of different mineral over time)

-> add day / night cycle (change the luminosity). Solar panel yield depend of sun output.

-> add some cloud that slowly move left and right across the display. maybe some bird too (3 sprite to animate the flight. make a place holder sprite and I wlill draw it) make the cloud / bird (condor ?) distribution altitude dependent with more bird toward the ground, different kind of cloud as one climb up in altitude. The cloud should be randomly generated using perlin noise and be somewhat transparent.

-> Add a battery grid storage (also require very expensive to make battery factory + lithium electrolysis plant and expensive battery cell)

-> there is a grid carbon intensity bar. it shows how many kg/CO2 per Mwh does the electric grid produce. once the user start having his full energy consumption covered and start reinjecting its energy on the grid, the carbon intensity goes down for everybody. a graph on the graph plane show the emmission over time and the cimmuluated emission  due to the minning operation and buying kwh from the grid (Kwh are bought automatically as needed given there is enough cash. if we run out of cash -> same behaviour as strike except that the work keep working, just every machine stop.)

-> building a warehouse allow to first store mineral that cant be processed right now, and can be updated to set cash / coffee treshold underwhich the system auto sell whatever to ensure they stay at a minimum level (next upgrade allow to switch from fixed item selling like iron + copper metal / ore to whatever is more profitable at the moment)

-> the load menu should pop up a menu that allow to select which one. there should a rolling backup mechanism that is automatic (backup every 2 min. keep last 2 min, last 4 min, last 8 min, last 16 min, last 32 min, last 64 min, last 128 min and last 256 min.) and thus the player can choose which load to rollback to.

-> Lets implement a splashscreen that start from a far zoom so that we see the mountain summit with the slow moving cloud. 
there is a title (Andes Mining Corp) and a press space to start. when space is pressed, it zoom in to 0,0. and the game start in x1.