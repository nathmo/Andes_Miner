All items below are implemented (one commit each). Kept as a record.

-> [x] create a repo with game screen shot / doc / readme / instruction and a github action that compile a .exe, .deb and MacOS app when pushing change.
-> PAUSE HERE, from now one, each of theses point should be made into a commit so that if anything break we can revert easily.

-> [x] add sprite for iced coffee, rename coffee to iced coffee. (use an emoji for now, export it to png)
-> [x] add sprite for jammies ( a blue circular coin)
-> [x] make the wage action based and not time based. (like 10 tile action = 1 iced coffee ) so the game is not time pressured.
-> [x] make the cleaning of rubble drop a rubble entity that need to be picked up.
-> [x] add select animation for cleaning rubble (to know which one are currently scheduled for cleaning like its done for mining).do the same for the roads when they are scheduled for construction.
-> [x] for the excavated texture, make it differentiated based on the original tile (excavated andesite dont look the same as excavated basalte)
-> [x] road shoudl cost rubble that need to be brought to site to be converted to road
-> [x] need to add a medium machine to build the road without a human worker
-> [x] Need to add a starting building that serve as a storage (so they dont just drop entity on the road in 0,0)
-> [x] need to add a new building that allow to plan mining operation automatically ( so that we can drag and select large area to mine and once this building exist, the planning of mining and road building to reach the requested ore can be automated.)
-> [x] need to make vehicle and worker find the shortes path timewise (aka use the road to go faster) if not done aldready. If it was done aldready, it mean we need to slow down more the rubble and make the road faster they the excavated rock.
-> [x] vehicle of first tier can mine rock whithin 2 tile, medium one can go 3 tile, the mega machine can do 4 tile away
-> [x] cargo vehicle have a capacity that depend of tier. small one can do only carry one item. medium can carry 3, large can carry 9 item. (and thus for the mega machine, we can keep mining/cleaning rubble and only drop the ore/rubble once fully full)
-> [x] need to make machine of higher tier much more expensive and every machine should much slower to give an incentive to build more than one (having a processing time that make sense so that its fun and not impossible to saturate).


-> [x] need to implement cable car, they go in straight line back to the center house, use to increase troughput of ore transporter as they can get quite slow once we are far away from center coord. come as a building pair. can only be built on road.

-> [x] there should be an overarching goal that give a sense of direction (villages to connect by road — lightweight goal, infinite map kept).

-> [x] when pointing a tile, it should also give info on the item dropped on it ( is it rubble ? iron ore ? copper ore ? ...) and excavated tile will not drop anything thus should not display that they contain ore.

-> [x] some other meterial to mine — SiO2 from rubble, lithium salt patches (spodumene) -> lithium; solar panels for energy generation reducing bought kWh.

-> [x] a market where we can buy and sell material we dont have (silicon/lithium bought; higher-tier vehicles require them; start with cash capital).

-> [x] a "stock market" with varying price (random fluctuation + production-driven trend; price floor; panel with prices and trends over time).

-> [x] day / night cycle (change the luminosity). Solar panel yield depend of sun output.

-> [x] clouds that slowly move + birds (condors, 3 flight frames, placeholder sprites); altitude-dependent distribution; semi-transparent noise clouds.

-> [x] Battery grid storage (Battery Factory + lithium electrolysis + battery cells).

-> [x] grid carbon intensity bar; emissions graph (rate + cumulative); auto-buy kWh; run out of cash -> machines stop, workers keep going.

-> [x] Warehouse: store minerals + auto-sell under cash/coffee thresholds; upgrade to sell whatever is most profitable.

-> [x] load menu to pick a save; rolling automatic backups (every 2 min; keep 2/4/8/16/32/64/128/256-min snapshots).

-> [x] Splashscreen: far zoom on the summit with slow clouds; title (Andes Mining Corp) + press space to start; SPACE zooms in to 0,0 and the game starts at x1.

-> [x] side panel buttons ran off-screen: split it into Build / Fleet / Trade tabs (money+coffee always in the top bar; wheel scrolls a tab if it overflows).

-> [x] split the combined Mine/Clean tool into three distinct action buttons — Excavate (rock), Clean (rubble), Road — in the bottom bar (shortcuts M/E, C, R).
