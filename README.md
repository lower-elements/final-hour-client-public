# final-hour

A COD inspired audiogame where players fight it out with zombies (online) for the highest kill counts, scores and of course greatest amount of enjoyment. 

## Running from source

Pipenv is a tool that helps manage Python dependencies. To install Pipenv, you can use pip:

```sh
pip install pipenv
```

Once Pipenv is installed, you can install the dependencies for this project by running:

```sh
pipenv install
```

This will install all of the dependencies specified in the Pipfile.

To play the game, run the command below in the root folder of this repository on a Windows machine:

```sh
pipenv run python final_hour.py
```

This will run the game using the dependencies installed in the virtual environment.

## Build the game.

First, please edit libs/version.py, changing the version to something compatible with semantic versioning, by changing the major, miner or patch arguments for the initializer you'll find there. 

now, commit the change you have just made to that file.

Next, tag the release:

```sh
git tag X.Y.Z -am "Release X.Y.Z"
```

Where `X`, `Y`, and `Z` are the major, minor, and patch numbers, respectively.

Then, you could run the following command to build the executable: 

```sh
pipenv run build.bat
```

## Makeshift design information (please follow).

Projects with more than one person working on them tend to fail in the absence of a form of a document that everyone could follow for design decisions, because everyone would otherwise wish to pull the project in a path of his own choosing. This section strives to be such, albeit it may not be entirely complete. This is not to say I don't appreciate your choices; it's just to keep order. Please attempt to prioritize and apply what you've learnt as much as possible.

This game is highly influenced by the zombies mode present in the games Call of Duty: World at War and Call of Duty: Black Ops 1–4. There are three primary timelines in the zombies mode. the aether, the dark aether, and the chaos timeline. We are solely concerned with the aether timeline.

While we may not clone most or all maps, nor will we utilize the plot significantly, we will almost exactly copy weapons, equipment, some gameplay micanics, weapon and item stats. We will also use quote lines from the original characters.

The following resources can help you learn about the zombies mode, the aether plot, and gain accurate weapon, item stats, and mathematical formulae for that mode.

[This](https://www.youtube.com/watch?v=cP0bQGrQZlc) 6-plus-hour video explain's the whole aether timeline, from beginning to end. While we won't utilize much of the plot itself, knowing everything about what you're trying to replicate is helpful. It also goes into great detail on the creation of the in-game micanics and how they relate to the plot.

[This](https://callofduty.fandom.com/wiki/Zombies_(Treyarch)) wiki article discusses several of the micanics utilized in the zombies mode. This entire wiki is the most valuable resource on weapons, items, and weapon and item stats. You may search for the weapons you need, and each weapon has its own page with stats, history, and anything else relevant to it. Please make sure to only look for and use weapons / items found in the zombies mode in the aether timeline.

