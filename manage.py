#!/usr/bin/env python3
"""Utilidad de línea de comandos de Django para Nodo Ruta."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nodoruta_web.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
