import os
import glob
from bs4 import BeautifulSoup

DOCS_DIR = "docs"
OUTPUT_FILE = os.path.join(DOCS_DIR, "merged_docs.html")

# 1. Buscar todos los HTML generados por pdoc
html_files = glob.glob(os.path.join(DOCS_DIR, "**/*.html"), recursive=True)
html_files.sort()  # opcional: orden alfabético


def rewrite_paths(soup, base_path):
    """
    Ajusta rutas relativas de <link>, <script>, <img>, <a>.
    """
    for tag in soup.find_all(["link", "script", "img", "a"]):
        attr = "href" if tag.name in ["link", "a"] else "src"
        if tag.has_attr(attr):
            url = tag[attr]
            # ignorar rutas absolutas o completas (http, https, #, mailto)
            if url.startswith(("http", "https", "#", "mailto")):
                continue

            # reconstruir ruta relativa desde docs/
            new_path = os.path.normpath(os.path.join(base_path, url))
            tag[attr] = new_path


# 2. Crear HTML unificado
with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
    out.write("<html><head><meta charset='utf-8'>\n")
    out.write("<title>Documentación Unificada</title>\n")
    out.write("</head><body>\n")
    out.write("<h1>Documentación Unificada</h1>\n")

    # 3. Insertar cada archivo HTML dentro del final
    for file in html_files:
        rel_path = os.path.relpath(file, DOCS_DIR)
        base_path = os.path.dirname(rel_path)

        out.write(f"<h2>📄 {rel_path}</h2>\n")

        with open(file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Ajustar rutas
        rewrite_paths(soup, base_path)

        # Escribir contenido
        out.write(str(soup))
        out.write("<hr style='margin:40px 0;'>\n")

    out.write("</body></html>")