GENERAL NOTE : FOR EACH TASK MAKE A COMMIT

-> [x] Cloud and bird are attach to display -> when zooming, the bird and cloud dont scale... and shift left and right. (world-anchored: clouds/birds now scale with zoom and pan with the map)

-> [x] the cloud are not thick enouugh (height wise) and way too common / dense. same for the bird lower the density. (taller cloud sprite; cloud + bird density lowered)

-> [x] make the bird trajectory not just lattera but more random (still in straigh line but also some diagonal. not horizontal only) (each condor flies a varied diagonal straight line)

-> [x] when pausing the bird and cloud should also pause. (sky is driven by sim time, so pause freezes it and speed scales it)

-> [x] add a clock and calendar (start the calendar at today date. each each game hourse should last about 30 second in x1 time) (top-bar clock + calendar, 30s = 1 game hour, day/night synced)

-> [x] add to the market an option to buy rubbles. (Buy Rubble in the Trade tab)

-> [x] show the price of electricity in the trend (and in the config define how many KWH / operation are required for each machine) (electricity price drifts + charted in the market panel; config.MACHINE_KWH_PER_OP)

-> [x] if a road job is missing rubble, say rubble shortage. (same style as strike) (amber RUBBLE SHORTAGE in the top bar + log)

-> [x] make sure that if there is no more cash to buy electricity, there is an error message like electric black out, buy some energy. (same style as strike) (red BLACKOUT in the top bar + log)

Also done this pass:
-> [x] the bottom action bar looked "gone": the 800px-tall window overflowed short (1366x768) screens, hiding it behind the taskbar. The window now fits the desktop on startup.
-> [x] Settings menu: Save game + Save & Quit buttons.
