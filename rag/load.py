"""Carga de documentos desde data/ — Deporte municipal (Madrid).

Convierte cada fichero del corpus en objetos Document de LangChain,
eligiendo el loader según su NOMBRE (para los CSV, que necesitan trato
distinto entre sí) o su EXTENSIÓN (para PDF).

Fuentes soportadas:
  - CSV_CENTROS   (polideportivos, instalaciones básicas, piscinas):
    mismo esquema de columnas -> una ficha de texto por centro/instalación.
  - XLSX_TARIFAS: una fila de tarifa -> un texto legible con precio y
    descuentos.
  - CSV_DESCUENTOS: 110k+ filas de USO (no de reglas). Se agregan por
    "Grupo de descuento" en unos pocos documentos-resumen, en vez de
    convertir cada fila en un chunk.
  - PDFs (reglamento, precios públicos, tarifas, infografía ADM):
    PyPDFLoader estándar.
"""

from collections import defaultdict
from pathlib import Path
import re

import pandas as pd
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from .config import (
    CSV_CENTROS,
    CSV_DESCUENTOS,
    DATA_DIR,
    EXTENSIONES_PDF,
    XLSX_TARIFAS,
)


def _valor(fila, columna: str) -> str:
    """Lee una celda y la devuelve como texto limpio, o '' si está vacía/NaN."""
    valor = fila.get(columna) if hasattr(fila, "get") else fila[columna]
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        # pandas lee columnas numéricas (p. ej. NUM de calle) como float
        return str(int(valor))
    return str(valor).strip()


# ---------------------------------------------------------------------------
# CSV de centros/instalaciones (polideportivos, instalaciones básicas, piscinas)
# ---------------------------------------------------------------------------


def _direccion(fila) -> str:
    partes = [
        _valor(fila, "CLASE-VIAL"),
        _valor(fila, "NOMBRE-VIA"),
        _valor(fila, "NUM"),
    ]
    return " ".join(p for p in partes if p).strip()


def fila_centro_a_texto(fila) -> str | None:
    """Convierte UNA fila de centro/instalación deportiva en texto legible."""
    nombre = _valor(fila, "NOMBRE")
    if not nombre:
        return None

    lineas = [f"Centro/instalación: {nombre}"]

    distrito = _valor(fila, "DISTRITO")
    barrio = _valor(fila, "BARRIO")
    if distrito or barrio:
        lineas.append(f"Distrito: {distrito or '?'} · Barrio: {barrio or '?'}")

    direccion = _direccion(fila)
    if direccion:
        lineas.append(f"Dirección: {direccion}")

    horario = _valor(fila, "HORARIO")
    if horario:
        lineas.append(f"Horario: {horario}")

    equipamiento = _valor(fila, "EQUIPAMIENTO")
    if equipamiento:
        lineas.append(f"Equipamiento: {equipamiento}")

    transporte = _valor(fila, "TRANSPORTE")
    if transporte:
        lineas.append(f"Transporte: {transporte}")

    accesibilidad = _valor(fila, "ACCESIBILIDAD")
    if accesibilidad:
        lineas.append(f"Accesibilidad: {accesibilidad}")

    telefono = _valor(fila, "TELEFONO")
    email = _valor(fila, "EMAIL")
    if telefono or email:
        lineas.append(f"Contacto: {telefono or '?'} · {email or '?'}")

    return "\n".join(lineas)


def cargar_centros_csv(ruta: Path, tipo_fuente: str) -> list[Document]:
    """Lee un CSV de centros/instalaciones: un Document por fila válida.

    tipo_fuente identifica de qué dataset viene (polideportivo,
    instalacion_basica, piscina), aunque las tres compartan columnas.
    """
    df = pd.read_csv(ruta, sep=";", encoding="latin-1")

    documentos: list[Document] = []
    for _, fila in df.iterrows():
        texto = fila_centro_a_texto(fila)
        if texto is None:
            continue

        metadata = {
            "source": str(ruta),
            "tipo_fuente": tipo_fuente,
            "nombre": _valor(fila, "NOMBRE"),
            "distrito": _valor(fila, "DISTRITO") or None,
            "barrio": _valor(fila, "BARRIO") or None,
        }
        documentos.append(Document(page_content=texto, metadata=metadata))

    return documentos


# ---------------------------------------------------------------------------
# XLSX de tarifas
# ---------------------------------------------------------------------------


def fila_tarifa_a_texto(fila) -> str | None:
    """Convierte UNA fila de tarifa en texto legible (precio + descuentos)."""
    servicio = _valor(fila, "Denominación del servicio")
    if not servicio:
        return None

    lineas = [f"Servicio: {servicio}"]

    grupo = _valor(fila, "Grupo de actividad")
    categoria = _valor(fila, "Categoría de edad")
    if grupo or categoria:
        lineas.append(f"Grupo: {grupo or '?'} · Categoría de edad: {categoria or '?'}")

    caracteristicas = _valor(fila, "Características")
    if caracteristicas:
        lineas.append(f"Características: {caracteristicas}")

    tarifa = _valor(fila, "Tarifa")
    if tarifa:
        lineas.append(f"Tarifa: {tarifa} €")

    observaciones = _valor(fila, "Observaciones")
    if observaciones:
        lineas.append(f"Observaciones: {observaciones}")

    desc_familia = _valor(fila, "Descuento familia numerosa")
    if desc_familia:
        lineas.append(f"Descuento familia numerosa: {desc_familia}")

    descuento = _valor(fila, "Descuento")
    motivo = _valor(fila, "Motivo del descuento")
    if descuento:
        pct = f"{float(descuento) * 100:.0f}%" if _es_numero(descuento) else descuento
        lineas.append(f"Descuento: {pct}" + (f" ({motivo})" if motivo else ""))

    return "\n".join(lineas)


def _es_numero(valor: str) -> bool:
    try:
        float(valor)
        return True
    except ValueError:
        return False


def cargar_tarifas_xlsx(ruta: Path) -> list[Document]:
    """Lee el XLSX de tarifas: un Document por fila de servicio/tarifa."""
    df = pd.read_excel(ruta)

    documentos: list[Document] = []
    for _, fila in df.iterrows():
        texto = fila_tarifa_a_texto(fila)
        if texto is None:
            continue

        metadata = {
            "source": str(ruta),
            "tipo_fuente": "tarifa",
            "grupo_actividad": _valor(fila, "Grupo de actividad") or None,
            "servicio": _valor(fila, "Denominación del servicio") or None,
        }
        documentos.append(Document(page_content=texto, metadata=metadata))

    return documentos

# ---------------------------------------------------------------------------
# Limpieza de texto (antes del chunking)
# ---------------------------------------------------------------------------


def normalizar_texto(texto: str) -> str:
    """Deja el texto listo para fragmentar: menos ruido, mismas frases."""
    if not texto:
        return ""

    t = texto.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\n{3,}", "\n\n", t)  # no más de una línea en blanco seguida
    t = re.sub(r"[ \t]+", " ", t)  # espacios/tabs repetidos -> uno solo
    t = "\n".join(linea.strip() for linea in t.split("\n"))
    return t.strip()


def limpiar_documentos(documentos: list[Document]) -> list[Document]:
    """Aplica normalizar_texto a cada documento; omite los que quedan vacíos."""
    limpios: list[Document] = []
    for doc in documentos:
        contenido = normalizar_texto(doc.page_content)
        if not contenido:
            continue
        limpios.append(Document(page_content=contenido, metadata=dict(doc.metadata)))
    return limpios

# ---------------------------------------------------------------------------
# CSV de descuentos (110k+ filas de USO -> se agrega, no se chunkea fila a fila)
# ---------------------------------------------------------------------------


def cargar_descuentos_agregado(ruta: Path) -> list[Document]:
    """Agrega el CSV de uso de descuentos por 'Grupo de descuento'.

    Este fichero NO contiene reglas de descuento en texto: son registros de
    cuántas veces se aplicó cada grupo de descuento, en qué centro, mes y
    sexo. Convertirlo fila a fila generaría decenas de miles de chunks casi
    idénticos, así que se resume en un puñado de documentos (uno por grupo).
    """
    df = pd.read_csv(ruta, sep=";", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    df["Grupo de descuento"] = df["Grupo de descuento"].astype(str).str.strip()
    df = df[df["Grupo de descuento"] != ""]
    df = df[df["Grupo de descuento"].str.lower() != "nan"]

    documentos: list[Document] = []
    for grupo, sub in df.groupby("Grupo de descuento"):
        total_usos = pd.to_numeric(sub["Nº Descuentos"], errors="coerce").sum()
        centros_top = (
            sub["Centro deportivo"].astype(str).str.strip().value_counts().head(5)
        )
        actividades = sorted(
            a for a in sub["Grupo de actividad deportiva"].astype(str).str.strip().unique() if a
        )

        lineas = [
            f"Grupo de descuento: {grupo}",
            f"Total de descuentos aplicados (registros de uso, no reglas): {int(total_usos)}",
            "Actividades donde se ha aplicado: " + ", ".join(actividades),
            "Centros deportivos con más uso de este descuento: "
            + ", ".join(f"{c} ({n})" for c, n in centros_top.items()),
        ]

        documentos.append(
            Document(
                page_content="\n".join(lineas),
                metadata={
                    "source": str(ruta),
                    "tipo_fuente": "descuento_uso_agregado",
                    "grupo_descuento": grupo,
                },
            )
        )

    return documentos


# ---------------------------------------------------------------------------
# Carga del corpus completo
# ---------------------------------------------------------------------------


def cargar_archivo(ruta: Path) -> list[Document]:
    """Elige el loader según el NOMBRE (CSV) o la EXTENSIÓN (PDF) del archivo."""
    nombre = ruta.name
    sufijo = ruta.suffix.lower()

    if nombre in CSV_CENTROS:
        return cargar_centros_csv(ruta, tipo_fuente=CSV_CENTROS[nombre])

    if nombre == XLSX_TARIFAS:
        return cargar_tarifas_xlsx(ruta)

    if nombre == CSV_DESCUENTOS:
        return cargar_descuentos_agregado(ruta)

    if sufijo in EXTENSIONES_PDF:
        return PyPDFLoader(str(ruta)).load()

    return []


def cargar_documentos() -> list[Document]:
    """Recorre data/ y concatena todos los Document soportados."""
    data_dir = Path(DATA_DIR)  # config.py lo define como string ("data")
    if not data_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de datos: {data_dir}")

    documentos: list[Document] = []
    for ruta in sorted(data_dir.rglob("*")):
        if not ruta.is_file():
            continue
        if ruta.name == "README.md":
            continue

        docs = cargar_archivo(ruta)
        if docs:
            print(f"  Cargado: {ruta.name} ({len(docs)} documento(s))")
            documentos.extend(docs)
        elif ruta.suffix:
            print(f"  [omitido] no reconocido: {ruta.name}")

    return documentos
