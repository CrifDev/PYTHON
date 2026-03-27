import PyInstaller.__main__
import os

dossier_actuel = os.path.dirname(os.path.abspath(__file__))
main_path = os.path.join(dossier_actuel, 'main.py')
icon_path = os.path.join(dossier_actuel, 'logo.ico')

print(f"Démarrage de la forge (Mode Rapide) dans : {dossier_actuel}")

add_data_string = f"{icon_path};."

PyInstaller.__main__.run([
    main_path,
    '--onedir', # <--- LA MAGIE EST ICI : On crée un dossier au lieu d'une valise
    '--noconsole',
    '--name=DenisChrono',
    f'--icon={icon_path}',
    f'--add-data={add_data_string}',
    f'--distpath={os.path.join(dossier_actuel, "dist")}', 
    f'--workpath={os.path.join(dossier_actuel, "build")}' 
])

print("Compilation express terminée ! Va voir dans le dossier 'dist'.")