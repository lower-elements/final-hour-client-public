# Final Hour

Final Hour is an open-source, audio-based game inspired by the Zombies mode in the Call of Duty series. Players can team up online to fight off hordes of zombies, aiming for high scores, kill counts, and an enjoyable experience.

## Features

*   **Online Co-op Gameplay:** Play with friends and other players online to survive against the undead.
*   **Inspired by Call of Duty Zombies:** Experience gameplay mechanics, weapons, and items reminiscent of the Aether timeline in the Call of Duty Zombies series.
*   **Immersive Audio Experience:** Designed as an audio game, Final Hour provides a rich and immersive soundscape for players.
*   **Cross-Platform:** While primarily developed on Windows, the game is built with cross-platform compatibility in mind.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

Before you begin, ensure you have [Pipenv](https://pipenv.pypa.io/en/latest/) installed. If you don't have it, you can install it using pip:

```sh
pip install pipenv
```

### Installation

1.  Clone the repository to your local machine:

    ```sh
    git clone https://github.com/lower-elements/final-hour-client-public.git
    ```

2.  Navigate to the project directory:

    ```sh
    cd final-hour-client-public
    ```

3.  Install the project dependencies using Pipenv:

    ```sh
    pipenv install
    ```

### Running the Game

To play the game, run the following command in the project's root directory on a Windows machine:

```sh
pipenv run python final_hour.py
```

## Building the Game

To build an executable version of the game, follow these steps:

1.  **Update the Version:** Before building, edit `libs/version.py` to set a new version number, following semantic versioning (e.g., `major.minor.patch`).

2.  **Commit the Version Change:** Commit the updated `libs/version.py` file to your local Git repository.

3.  **Tag the Release:** Create a new Git tag for the release:

    ```sh
    git tag -a X.Y.Z -m "Release X.Y.Z"
    ```

    Replace `X.Y.Z` with the version number you set in `libs/version.py`.

4.  **Run the Build Script:** Execute the build script to create the game executable:

    ```sh
    pipenv run build.bat
    ```

## Contributing

Contributions are welcome! If you'd like to contribute to Final Hour, please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes and commit them with clear, descriptive messages, following convencional commits.
4.  Push your changes to your forked repository.
5.  Create a pull request to the main repository's `main` branch.

Please ensure your code adheres to the project's existing code style and conventions.

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for more details.

## Acknowledgments

*   This project is heavily inspired by the Zombies mode in the Call of Duty series, particularly the Aether storyline.
*   We utilize resources from the Call of Duty fan community for weapon stats, character quotes, and gameplay mechanics.
*   A special thanks to the creators of the original Call of Duty Zombies for their incredible work.
