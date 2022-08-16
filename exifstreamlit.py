# Exercice      : 4.2
# Cours         : L1 Outils informatiques collaboratifs, DN22ET01
# Auteur        : Sebastien Andrivet - 20013599
# Fichier       : exifstreamlit.py
# Description   : Streamlit Application
# Version       : 1.0
# Date          : 2022-08-11
import sys
import os.path
from datetime import datetime
from enum import Enum
from typing import Any, Tuple
import streamlit as st
from PIL import Image
from exif import Image as ExifImage, Flash
from streamlit_folium import st_folium
import folium


# Les tags à ignorer
fields_ignore = ['_exif_ifd_pointer', '_gps_ifd_pointer', 'maker_note', 'scene_type']
# Les champs que l'on ne peut pas écrire
fields_read_only = ['exif_version', 'jpeg_interchange_format', 'jpeg_interchange_format_length']


def pretty_name(name: str) -> str:
    """Conversion d'un nom (tag) pour l'affichage"""
    return name[0].upper() + name[1:].lower().replace('_', ' ')


def is_int(value: str) -> bool:
    """Indique si une chaine représente un entier"""
    return value[1:].isdecimal() if value.startswith('-') or value.startswith('+') else value.isdecimal()


def is_float(value: str) -> bool:
    """Indique si une chaine représente un float"""
    try:
        float(value)
    except ValueError:
        return False
    return True


def create_text_input(tag: str, value: str, readonly: bool) -> str:
    """Crée une entrée de texte"""
    return st.text_input(pretty_name(tag), value=value, disabled=readonly)


def create_int_input(tag: str, value: int, readonly: bool) -> int:
    """Crée une entrée d'entier"""
    return st.number_input(pretty_name(tag), value=value, disabled=readonly)


def create_float_input(tag: str, value: float, readonly: bool) -> float:
    """Crée une entrée de float"""
    return st.number_input(pretty_name(tag), value=value, format='%.2f', disabled=readonly)


def create_boolean_input(tag: str, value: bool, readonly: bool) -> bool:
    """Crée une entrée Vrai / Faux"""
    return bool(st.selectbox(pretty_name(tag), ['False', 'True'], index=1 if value else 0, disabled=readonly))


def create_date_input(tag: str, value: str, readonly: bool) -> str:
    """Crée une entrée pour une date et une heure"""
    value = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    st.write(pretty_name(tag))
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input('Date', value=value, key=tag + '.date', disabled=readonly)
    with col2:
        time = st.time_input('Time', value=value, key=tag + '.time', disabled=readonly)
    return datetime.combine(date, time).strftime("%Y:%m:%d %H:%M:%S")


def create_options_input(tag: str, value: Enum, readonly: bool) -> Enum:
    """Crée une entrée avec un choix dans une liste"""
    value_type = type(value)
    values = list(value_type)
    labels = [pretty_name(i.name) for i in value_type]
    index = values.index(value)
    option = st.selectbox(pretty_name(tag), labels, index=index, disabled=readonly)
    index = labels.index(option)
    return values[index]


def create_flash(flash: Flash) -> None:
    """Crée les entrées pour un objet Flash"""
    st.write('Flash')
    with st.expander("Flash"):
        flash.flash_fired = create_boolean_input('flash_fired', flash.flash_fired, False)
        flash.flash_function_not_present = create_boolean_input('flash_function_not_present',
                                                                flash.flash_function_not_present, False)
        flash.flash_mode = create_options_input('flash_mode', flash.flash_mode, False)
        flash.flash_return = create_options_input('flash_return', flash.flash_return, False)
        flash.red_eye_reduction_supported = create_boolean_input('red_eye_reduction_supported',
                                                                 flash.red_eye_reduction_supported, False)


def create_tuple(tag: str, value: Tuple[Any], readonly: bool) -> Tuple[Any]:
    """Crée des entrées pour un tuple"""
    st.write(pretty_name(tag))
    nb_cols = len(value)
    cols = st.columns(nb_cols)
    out = []
    for i in range(nb_cols):
        with cols[i]:
            out.append(create_input(f'Value #{i}', value[i], readonly))
    return tuple(out)


def create_input(tag: str, value: Any, readonly: bool) -> Any:
    """Crée une ou des entrées en fonction du type de la valeur"""

    # On teste les différents cas
    if isinstance(value, Enum):
        return create_options_input(tag, value, readonly)
    elif isinstance(value, float):
        return create_float_input(tag, value, readonly)
    elif isinstance(value, int):
        return create_int_input(tag, value, readonly)
    elif isinstance(value, bool):
        return create_boolean_input(tag, value, readonly)
    elif isinstance(value, tuple):
        return create_tuple(tag, value, readonly)
    elif tag.startswith("datetime"):
        return create_date_input(tag, value, readonly)
    elif isinstance(value, str):
        return create_text_input(tag, value, readonly)
    elif tag == 'flash':
        create_flash(value)
    else:
        print(f'Unknown type {type(value)} for tag {tag}')

    return None


def load(path: str) -> ExifImage:
    """Charge une image et l'affiche"""
    image = Image.open(path)
    st.image(image, caption=path)

    with open(path, 'rb') as f:
        img = ExifImage(f)
    return img


def display(img: ExifImage) -> None:
    """Affiche les champs EXIF d'une image et met à jour suivant les entrées de l'utilisateur"""
    tags = img.list_all()
    for tag in tags:
        try:
            if tag not in fields_ignore:
                value = img[tag]  # La valeur pour laquelle on veut créer une entrée
                readonly = tag in fields_read_only
                out = create_input(tag, value, readonly)  # On crée l'entrée
                try:
                    # S'il y a une sortie et que l'on peut l'écrire...
                    if out is not None and tag not in fields_read_only:
                        img[tag] = out
                except TypeError as e:
                    print(tag, e)  # Il y a un bug quelque part, on ignore silencieusement
                except ValueError as e:
                    st.error(e)  # La valeur entrée par l'utilisateur n'est pas valide
                except RuntimeError as e:
                    print(tag, e)  # Cas d'un champ read-only par exemple
        except NotImplementedError as e:
            print(tag, e)  # On ne peut pas lire ce champ, on ignore silencieusement


def save(path: str, img: ExifImage) -> None:
    """Save une image modifiée"""
    if st.button("Save"):
        full_name = os.path.basename(path)
        name_ext = os.path.splitext(full_name)
        new_path = os.path.dirname(path) + name_ext[0] + "-modified" + name_ext[1]
        with open(new_path, 'wb') as new_image_file:
            new_image_file.write(img.get_file())
        st.success(f'File {new_path} saved')


def gps_convert(deg: int, min: int, sec: float, dir: str):
    """Conversion des coordonnées GPS"""
    value = float(deg) + float(min) / 60 + float(sec) / 3600
    return -value if dir == 'S' or dir == 'W' else value


def gps_convert_tuple(gps: Tuple, dir: str):
    """Conversion des coordonnées GPS"""
    return gps_convert(gps[0], gps[1], gps[2], dir)


def show_map(path: str, img: ExifImage) -> None:
    """Affiche un plan centrée sur le lieu de prise d'une image"""
    st.subheader("Emplacement de la prise de la photo")
    latitude = gps_convert_tuple(img.gps_latitude, img.gps_latitude_ref)
    longitude = gps_convert_tuple(img.gps_longitude, img.gps_longitude_ref)
    m = folium.Map(location=[latitude, longitude], zoom_start=10)
    folium.Marker([latitude, longitude],
                  tooltip=path).add_to(m)
    st_folium(m, width=800)


# Lieux d'habitation ou de voyage
past_locations = [
    [46.17755679583263, 6.0770121088625935, 'Genève'],
    [45.90868517199744, 6.1293218436282695, 'Annecy'],
    [48.86554547844242, 2.340162557342804, 'Paris'],
    [38.29257297153023, 23.701870699664667, 'Athene'],
    [40.84749907078552, -73.97399537707226, 'New-York City'],
    [51.507797069177364, -0.12634020608442303, 'London'],
    [-4.330771319222508, 15.247891952109715, 'Kinshasa'],
    [16.883686402505532, -24.98776016924694, 'Mindelo'],
    [50.11735279941898, 8.64066084172503, 'Frankfurt'],
    [-33.883023330969756, 151.2004531447457, 'Sydney'],
    [49.280052534422026, -123.09781741547766, 'Vancouver'],
    [42.65752230220411, 21.165592095905076, 'Pristina'],
    [-8.83209527007044, 13.24636360674181, 'Luanda'],
    [0.045289158446527145, -78.47755931234315, 'Quito'],
    [10.753372379542352, -66.89014120843507, 'Caracas'],
    [36.43712668084, 28.221187430206413, 'Rhodes'],
    [42.90967631051445, 74.58644702539533, 'Bishkek']
]


def show_trips() -> None:
    """Affiche sur une carte du monde les lieux de voyage ou d'habitation"""
    st.subheader("Lieux d'habitation et voyages")
    points = [[p[0], p[1]] for p in past_locations]
    m = folium.Map(width=800)
    for p in past_locations:
        folium.Marker([p[0], p[1]], tooltip=p[2]).add_to(m)
    folium.PolyLine(points).add_to(m)
    st_folium(m, width=800, height=400)


def main():
    # L'image à charger
    image_path = 'IMG_3197.jpg' if len(sys.argv) <= 1 else sys.argv[1]
    # Titre
    st.title("EXIF information")
    # On charge l'image
    exif_image = load(image_path)
    # On affiche les informations EXIF
    display(exif_image)
    # On sauve l'image modifiée
    save(image_path, exif_image)
    # On affiche le lieu de prise de l'image
    show_map(image_path, exif_image)
    # On affiche les lieux de voyage ou d'habitation
    show_trips()


if __name__ == '__main__':
    main()
