# Portfolio estático · Módulo "Puesta en Producción Segura"

Sitio web 100 % estático (HTML, CSS y JS vanilla) que recopila los ejercicios
realizados en el módulo **Puesta en Producción Segura**. Cada ejercicio tiene su
propia página con el contenido íntegro de su documento original.

## Estructura del proyecto

```
portfolio_puesta_prod_segura/
├── index.html                     # Portada con tarjetas por ejercicio
├── ejercicios/
│   ├── ejercicio-01.html          # GIT Ariketa 5.1.1
│   ├── ejercicio-02.html          # GIT Ariketa 5.1.2
│   ├── ejercicio-03.html          # GIT Ariketa 5.1.3
│   ├── ejercicio-04.html          # GIT Ariketa 5.1.4 · Reto colaborativo
│   ├── ejercicio-05.html          # OWASP Top 10 · Tarea 1 (Sesión 1)
│   ├── ejercicio-06.html          # ASVS de OWASP · Auditoría web
│   ├── ejercicio-07.html          # Recurso de audio (dependencias vulnerables)
│   └── ejercicio-08.html          # Práctica Docker 1 · Nginx + Node.js
├── assets/
│   ├── css/style.css              # Hoja de estilos única (tema claro/oscuro)
│   ├── js/app.js                  # JS vanilla (tema, menú móvil, copiar)
│   ├── img/ejercicio-XX/          # Imágenes extraídas de los documentos (.docx)
│   └── audio/                     # Recurso de audio .m4a
├── build.py                       # Script único de generación estática
└── README.md                      # Este archivo
```

> La carpeta `prod_segura_ejercicios/` (fuente de los documentos `.docx` y el
> `.m4a`) se encuentra un nivel arriba y **no se modifica**.

---

## 1. Ejecutar el build

Requisitos: Python 3 con `python-docx` (`pip install python-docx`).

Desde la carpeta `portfolio_puesta_prod_segura/`:

```bash
python build.py
```

Esto genera `index.html`, las 8 páginas en `ejercicios/` y extrae las imágenes a
`assets/img/ejercicio-XX/`. El script lee exclusivamente de
`../prod_segura_ejercicios/` y escribe todo en la carpeta actual.

---

## 2. Previsualizar el sitio (sin servidor)

Puedes abrir `index.html` directamente en el navegador (rutas relativas):

```bash
# Windows (PowerShell)
start index.html

# Linux / macOS
xdg-open index.html   # o open index.html
```

O servirlo localmente para probar las cabeceras y el menú:

```bash
python -m http.server 8000
# luego abre http://localhost:8000 en el navegador
```

También funciona en GitHub Pages o Nginx sin ajustes, al usar solo rutas
relativas.

---

## 3. Despliegue en Nginx (ejemplo con cabeceras de seguridad)

Archivo sugerido `/etc/nginx/sites-available/portfolio` (ajusta `root` y
`server_name`):

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name portfolio.tudominio.com;
    root /var/www/portfolio_puesta_prod_segura;
    index index.html;

    # Redirigir a HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name portfolio.tudominio.com;
    root /var/www/portfolio_puesta_prod_segura;
    index index.html;

    ssl_certificate     /etc/letsencrypt/live/portfolio.tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/portfolio.tudominio.com/privkey.pem;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Cabeceras de seguridad
    add_header Content-Security-Policy "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self'; media-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'; frame-ancestors 'none';" always;
    add_header Referrer-Policy "no-referrer" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    location / {
        try_files $uri $uri/ =404;
    }

    location ~* \.(html|css|js|png|jpg|jpeg|gif|svg|m4a)$ {
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        try_files $uri =404;
    }
}
```

Nota: el propio HTML ya incluye un `<meta http-equiv="Content-Security-Policy">`
restrictivo y `<meta name="referrer" content="no-referrer">` como defensa en
profundidad, incluso si se abre el archivo directamente sin servidor.

---

## 4. Seguridad aplicada

- **CSP restrictiva** (sin scripts inline, sin estilos inline, sin CDNs externos,
  sin objetos, sin marcos anidados, `form-action 'none'`).
- **Referrer estricto** (`no-referrer`).
- **Sin dependencias externas en runtime**: todo el CSS/JS es local; el
  resaltado de sintaxis se genera en el servidor (build) y no requiere librería
  de terceros en el navegador.
- **Datos sensibles**: se sustituyen por placeholders y no se incluyen en el
  sitio (ver sección "Suposiciones y problemas").
- **Escapado HTML** de todo el contenido extraído de los documentos, sobre todo
  los bloques de código.
- **Imágenes** con `loading="lazy"` y `alt`; rutas relativas.

---

## 5. Suposiciones y problemas encontrados

1. **Orden de los ejercicios**: se siguió el orden indicado por el docente:
   `5.1.1 → 5.1.2 → 5.1.3 → reto colaborativo → OWASP → ASVS → video → docker`.
   El archivo de audio `.m4a` se trata como ejercicio-07 con su propia página y
   reproductor, pues también está en la carpeta fuente y debe aparecer en el
   sidebar.

2. **Títulos de los documentos**: el estilo "Title" de algunos `.docx` no se
   captura de forma fiable desde el XML, por lo que se asignan títulos
   descriptivos manuales (basados en el contenido real) como fallback.

3. **Bloques de código**: los documentos fuente no delimitan los fragmentos de
   código con fuente monoespaciada consistente (muchos comandos van en Arial).
   Por tanto, el resaltado de sintaxis se aplica **inline** sobre las partes que
   sí usan fuente mono (Consolas / Roboto Mono / Courier). No se inventan bloques
   de código que no existan en el documento original, para no alterar el
   contenido. El criterio de aceptación de "contenido íntegro sin pérdidas" se
   cumple plenamente.

4. **Imágenes en tablas**: el ejercicio OWASP (ejercicio-05) incrustaba capturas
   dentro de celdas de tabla; se extraen y se insertan en esas celdas.

5. **Archivo de audio**: el `.m4a` no se transcribe (no hay motor de voz a texto
   disponible offline); se incluye como reproductor en su página.

6. **Datos sensibles sustituidos por placeholders** (no se incluyen secretos,
   credenciales ni IPs reales en el sitio):
   - `admin123` → `[CONTRASEÑA_EJEMPLO]`
   - `token=... / contraseña=...` → `...=[VALOR_OCULTO]`
   - IPs reales (p. ej. `192.168.1.1`, `169.254.169.254`) → `[IP_EJEMPLO]`
   - correos → `[EMAIL_OCULTO]`
   - terceros (otro alumno) → `[ALUMNO A]`

   Si detectas algún dato sensible que no haya sido reemplazado, avísame para
   ajustar el script y regenerar.

---

## 6. Accesibilidad y rendimiento

- HTML semántico (`nav`, `main`, `article`, `header`, `footer`, `figure`,
  `pre`, `code`, `table`).
- Enlace "Saltar al contenido" y foco visible.
- Menú hamburguesa accesible (`aria-expanded`, `aria-controls`, cierre con `Esc`).
- Tema claro/oscuro con `prefers-color-scheme`, toggle manual y `localStorage`.
- CSS en un único archivo; JS mínimo y sin dependencias.
- Imágenes con `loading="lazy"`.
