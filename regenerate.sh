#!/bin/bash
# Regenerates language files and adds them to Git before a commit.

if [ "$1" == "setup" ];
then
    echo "Setting this as a pre-commit hook."
    cp ./regenerate.sh ./.git/hooks/pre-commit
    echo "Done."
    exit
fi

langs=('en')
echo "Regenerating language files... (use --no-verify to skip)"
cd languages
for lang in ${langs[@]}; do
    python3 generate.py $lang
    echo "Adding language $lang to Git"
    git add $lang
done
echo "Adding template to Git"
git add TEMPLATE
echo "Done!"