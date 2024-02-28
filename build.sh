#!/bin/bash
python setup.py clean --all bdist_wheel
#conda init zsh 
#conda activate base
virtualenv dbdemos_build
#source dbdemos_build/bin/activate
.\\dbdemos_build\\Scripts\\activate
#pip install bin/dbsqlclone-0.1.24-py3-none-any.whl
pip install dist/dbdemos-0.3.44.jade.01-py3-none-any.whl --force
#python3 test_demo.py
python main.py

cp dist/dbdemos-* release/

.\\dbdemos_build\\Scripts\\deactivate.bat

rm -rf dbdemos_build