# -*- coding: utf8 -*-

import os
import sys


# Retorna 0 se tiver uma versao instalada do virtualenv.
# Retorna 1 se der erro
def virtualenv_installed():
    return os.system("virtualenv --version") == 0


# Gambiarra: checa se ja existe um arquivo cfg desse env.
def venv_exists(venv_name):
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), venv_name, "pyvenv.cfg")
    return os.path.exists(cfg)


# atualiza o env com os requirements
def update_virtualenv(venv_name):
    cmd = "cd {0}/{1}/Scripts& activate & py -m pip install -r \"{0}/requirement.txt\"".format(
        os.path.dirname(os.path.abspath(__file__)), venv_name).replace("\\", "/")
    return os.system(cmd) == 0


def init_virtual_env(venv_name):
    if not virtualenv_installed():
        if not os.system("py -m pip install virtualenv") == 0:
            print("falha ao instalar o virtualenv!")
            return False

    if not venv_exists(venv_name):
        cmd = "cd {0}& py -m virtualenv {1}& cd {0}/{1}& virtualenv .".format(
            os.path.dirname(os.path.abspath(__file__)), venv_name).replace("\\", "/")
        print(cmd)
        if not os.system(cmd) == 0:
            print("falha ao criar o virtual env:")
            return False
    else:
        print("virtual env ja instalado!")
        return True

    if not update_virtualenv(venv_name):
        print("falha ao instalar os modulos!")
        return False
    else:
        print("venv instalado com sucesso!")
        return True


def init(venv_name):
    try:
        install_venv = init_virtual_env(venv_name)
        return install_venv
    except Exception as e:
        print(e)
        return False


if __name__ == '__main__':
    args = sys.argv

    init(args[1])