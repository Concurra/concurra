rm -rf ./dist/

python3 -m build

# Upload to PyPI
python3 -m twine upload dist/*
