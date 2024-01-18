# Releasing

The following is a guide on the steps necessary to creating a release of `matrix-reminder-bot`.

1. Update the `__version__` variable in `matrix_reminder_bot/__init__.py`.

1. Store the version in an environment variable for convenience:

	```sh
	ver=`python3 -c 'import matrix_reminder_bot; print(matrix_reminder_bot.__version__)'`
	```

1. Create a release branch off of master:

	```sh
	git checkout -b release-v$ver
	```

1. Update `CHANGELOG.md` with the latest changes for this release.

1. Create a commit and push your changes to the release branch:

	```sh
	git add -u && git commit -m $ver -n && git push -u origin $(git symbolic-ref --short HEAD)
	```

1. Check that the changelog is rendered correctly:

	```sh
	xdg-open https://github.com/anoadragon453/matrix-reminder-bot/blob/release-v$ver/CHANGELOG.md
	```

1. Create a signed tag for the release:

	```sh
	git tag -s v$ver
	```

1. Push the tag:

	```sh
	git push origin tag v$ver
	```

	The commit message should just be the changelog entry, with `X.Y.Z` as the title.

1. Upload the release to PyPI:

	```sh
	python3 setup.py sdist bdist_wheel
	python3 -m twine upload dist/matrix_reminder_bot-$ver-py3-none-any.whl dist/matrix-reminder-bot-$ver.tar.gz
	```

1. Check that the images on Docker Hub are building: https://hub.docker.com/repository/docker/anoa/matrix-reminder-bot

1. Create the release on GitHub:

	```sh
	xdg-open https://github.com/anoadragon453/matrix-reminder-bot/releases/edit/v$ver
	```

1. Merge the release branch to `master`:

	```sh
	git checkout master && git merge release-v$ver
	```

1. Push to `master`.

	```sh
	git push origin master
	```

1. Announce release on https://matrix.to/#/#thisweekinmatrix:matrix.org

1. Celebrate!
