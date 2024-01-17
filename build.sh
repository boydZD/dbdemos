python3 setup.py clean --all bdist_wheel
#conda init zsh 
conda activate base
pip3 install dist/dbdemos-0.3.45-py3-none-any.whl --force
#python3 test_demo.py
python3 main.py

cp dist/dbdemos-* release/