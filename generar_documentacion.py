#!/usr/bin/env python3
"""
GENERADOR DE DOCUMENTACIÓN DEL PROYECTO VENDO_SRI
=================================================
Script para analizar y documentar completamente el proyecto.

Uso: python generar_documentacion.py
"""

import os
import datetime
import subprocess
import sys
from pathlib import Path

def ejecutar_comando(comando):
    """Ejecuta un comando y retorna la salida"""
    try:
        resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
        return resultado.stdout.strip() if resultado.returncode == 0 else "Error al ejecutar comando"
    except Exception as e:
        return f"Error: {str(e)}"

def obtener_tamaño_archivo(ruta):
    """Obtiene el tamaño de un archivo en formato legible"""
    try:
        tamaño = os.path.getsize(ruta)
        if tamaño == 0:
            return "0B"
        elif tamaño < 1024:
            return f"{tamaño}B"
        elif tamaño < 1024 * 1024:
            return f"{tamaño/1024:.1f}KB"
        else:
            return f"{tamaño/(1024*1024):.1f}MB"
    except:
        return "N/A"

def generar_arbol_directorios(directorio, prefijo="", max_profundidad=4, profundidad_actual=0):
    """Genera un árbol de directorios en formato texto"""
    if profundidad_actual > max_profundidad:
        return []
    
    resultado = []
    directorios_excluir = {"venv", ".git", "__pycache__", "node_modules", ".pytest_cache"}
    
    try:
        elementos = sorted(os.listdir(directorio))
        elementos = [e for e in elementos if not e.startswith('.') or e in {'.env', '.env.example', '.gitignore'}]
        
        for i, elemento in enumerate(elementos):
            ruta_completa = os.path.join(directorio, elemento)
            es_ultimo = i == len(elementos) - 1
            
            conector = "└── " if es_ultimo else "├── "
            nuevo_prefijo = prefijo + ("    " if es_ultimo else "│   ")
            
            if os.path.isdir(ruta_completa):
                if elemento in directorios_excluir:
                    resultado.append(f"{prefijo}{conector}{elemento}/ (excluido)")
                else:
                    contenido = len(os.listdir(ruta_completa)) if os.path.exists(ruta_completa) else 0
                    resultado.append(f"{prefijo}{conector}{elemento}/ ({contenido} elementos)")
                    
                    if profundidad_actual < max_profundidad:
                        sub_arbol = generar_arbol_directorios(
                            ruta_completa, nuevo_prefijo, max_profundidad, profundidad_actual + 1
                        )
                        resultado.extend(sub_arbol)
            else:
                tamaño = obtener_tamaño_archivo(ruta_completa)
                resultado.append(f"{prefijo}{conector}{elemento} ({tamaño})")
    
    except PermissionError:
        resultado.append(f"{prefijo}(Sin permisos de acceso)")
    except Exception as e:
        resultado.append(f"{prefijo}(Error: {str(e)})")
    
    return resultado

def verificar_archivo_existe(ruta):
    """Verifica si un archivo existe y retorna emoji"""
    return "✅" if os.path.exists(ruta) else "❌"

def contar_archivos_por_extension():
    """Cuenta archivos por extensión"""
    extensiones = {}
    for root, dirs, files in os.walk("."):
        # Excluir directorios específicos
        dirs[:] = [d for d in dirs if d not in {"venv", ".git", "__pycache__", "node_modules"}]
        
        for archivo in files:
            _, ext = os.path.splitext(archivo)
            ext = ext.lower() if ext else "(sin extensión)"
            extensiones[ext] = extensiones.get(ext, 0) + 1
    
    return dict(sorted(extensiones.items(), key=lambda x: x[1], reverse=True))

def obtener_paquetes_instalados():
    """Obtiene lista de paquetes instalados con pip"""
    try:
        resultado = ejecutar_comando("pip freeze")
        return resultado.split('\n') if resultado != "Error al ejecutar comando" else []
    except:
        return []

def verificar_paquete_instalado(paquete):
    """Verifica si un paquete específico está instalado"""
    resultado = ejecutar_comando(f"pip show {paquete}")
    if "Error" in resultado or not resultado:
        return False, "No instalado"
    
    # Extraer versión
    for linea in resultado.split('\n'):
        if linea.startswith('Version:'):
            version = linea.split(':')[1].strip()
            return True, version
    return True, "Versión desconocida"

def analizar_settings_django():
    """Analiza el archivo settings.py de Django"""
    settings_path = "vendo_sri/settings.py"
    if not os.path.exists(settings_path):
        return {"existe": False}
    
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        configuraciones = {
            "existe": True,
            "INSTALLED_APPS": "INSTALLED_APPS" in contenido,
            "DATABASES": "DATABASES" in contenido,
            "REST_FRAMEWORK": "REST_FRAMEWORK" in contenido,
            "STATIC_URL": "STATIC_URL" in contenido,
            "DEBUG": "DEBUG" in contenido,
            "SECRET_KEY": "SECRET_KEY" in contenido,
        }
        
        # Extraer INSTALLED_APPS si existe
        if configuraciones["INSTALLED_APPS"]:
            try:
                inicio = contenido.find("INSTALLED_APPS")
                if inicio != -1:
                    # Buscar el inicio de la lista
                    inicio_lista = contenido.find("[", inicio)
                    if inicio_lista != -1:
                        # Buscar el final de la lista (contando corchetes)
                        contador = 1
                        pos = inicio_lista + 1
                        while pos < len(contenido) and contador > 0:
                            if contenido[pos] == '[':
                                contador += 1
                            elif contenido[pos] == ']':
                                contador -= 1
                            pos += 1
                        
                        if contador == 0:
                            apps_texto = contenido[inicio:pos]
                            configuraciones["INSTALLED_APPS_contenido"] = apps_texto
            except:
                configuraciones["INSTALLED_APPS_contenido"] = "Error al extraer"
        
        return configuraciones
    except Exception as e:
        return {"existe": True, "error": str(e)}

def analizar_apps_django():
    """Analiza las aplicaciones Django en el directorio apps/"""
    if not os.path.exists("apps"):
        return []
    
    apps = []
    for app_dir in os.listdir("apps"):
        app_path = os.path.join("apps", app_dir)
        if os.path.isdir(app_path):
            archivos_basicos = ["models.py", "views.py", "urls.py", "admin.py", "apps.py"]
            archivos_existentes = []
            
            for archivo in archivos_basicos:
                if os.path.exists(os.path.join(app_path, archivo)):
                    archivos_existentes.append(archivo)
            
            # Contar todos los archivos en la app
            total_archivos = len([f for f in os.listdir(app_path) 
                                if os.path.isfile(os.path.join(app_path, f))])
            
            apps.append({
                "nombre": app_dir,
                "archivos_basicos": len(archivos_existentes),
                "total_basicos": len(archivos_basicos),
                "archivos_existentes": archivos_existentes,
                "total_archivos": total_archivos,
                "estado": "Completa" if len(archivos_existentes) == len(archivos_basicos) 
                         else "Parcial" if archivos_existentes else "Vacía"
            })
    
    return sorted(apps, key=lambda x: x["nombre"])

def generar_reporte():
    """Genera el reporte completo"""
    timestamp = datetime.datetime.now()
    nombre_archivo = f"DOCUMENTACION_VENDO_SRI_{timestamp.strftime('%Y%m%d_%H%M%S')}.txt"
    
    print("🔍 Analizando proyecto vendo_sri...")
    print(f"📄 Generando archivo: {nombre_archivo}")
    
    # Obtener información del sistema
    python_version = ejecutar_comando("python --version")
    pip_version = ejecutar_comando("pip --version")
    directorio_actual = os.getcwd()
    
    # Verificar entorno virtual
    entorno_virtual = os.environ.get('VIRTUAL_ENV')
    estado_venv = f"✅ ACTIVO ({entorno_virtual})" if entorno_virtual else "❌ NO ACTIVO"
    
    # Analizar estructura
    print("📁 Analizando estructura de directorios...")
    arbol = generar_arbol_directorios(".")
    
    print("📊 Contando archivos...")
    extensiones = contar_archivos_por_extension()
    
    print("📱 Analizando apps Django...")
    apps_django = analizar_apps_django()
    
    print("⚙️ Analizando configuración Django...")
    config_django = analizar_settings_django()
    
    print("📦 Verificando paquetes Python...")
    paquetes_instalados = obtener_paquetes_instalados()
    
    # Paquetes requeridos para el proyecto SRI
    paquetes_requeridos = {
        "Django": "4.2.7",
        "djangorestframework": "3.14.0",
        "psycopg2-binary": "2.9.7",
        "python-decouple": "3.8",
        "celery": "5.3.4",
        "redis": "5.0.1",
        "cryptography": "41.0.7",
        "lxml": "4.9.3",
        "zeep": "4.2.1",
        "reportlab": "4.0.7",
        "Pillow": "10.1.0",
        "drf-spectacular": "0.26.5"
    }
    
    # Verificar cada paquete requerido
    estado_paquetes = {}
    for paquete, version_req in paquetes_requeridos.items():
        instalado, version = verificar_paquete_instalado(paquete)
        estado_paquetes[paquete] = {
            "instalado": instalado,
            "version": version,
            "version_requerida": version_req
        }
    
    print("📝 Generando reporte...")
    
    # Generar contenido del reporte
    reporte = f"""
================================================================================
                    DOCUMENTACIÓN COMPLETA - PROYECTO VENDO_SRI
================================================================================

INFORMACIÓN GENERAL
-------------------
Fecha de generación: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Ubicación: {directorio_actual}
Python Version: {python_version}
Pip Version: {pip_version}
Entorno Virtual: {estado_venv}
Sistema Operativo: {os.name}
Usuario: {os.environ.get('USERNAME', os.environ.get('USER', 'Desconocido'))}

================================================================================
                            ESTRUCTURA DEL PROYECTO
================================================================================

{chr(10).join(arbol)}

================================================================================
                            ANÁLISIS DE ARCHIVOS
================================================================================

ARCHIVOS IMPORTANTES
--------------------
manage.py               {verificar_archivo_existe('manage.py')} {'Existe' if os.path.exists('manage.py') else 'Faltante'}
requirements.txt        {verificar_archivo_existe('requirements.txt')} {'Existe' if os.path.exists('requirements.txt') else 'Faltante'}
.env                    {verificar_archivo_existe('.env')} {'Existe' if os.path.exists('.env') else 'Faltante'}
.env.example            {verificar_archivo_existe('.env.example')} {'Existe' if os.path.exists('.env.example') else 'Faltante'}
.gitignore              {verificar_archivo_existe('.gitignore')} {'Existe' if os.path.exists('.gitignore') else 'Faltante'}
README.md               {verificar_archivo_existe('README.md')} {'Existe' if os.path.exists('README.md') else 'Faltante'}
docker-compose.yml      {verificar_archivo_existe('docker-compose.yml')} {'Existe' if os.path.exists('docker-compose.yml') else 'Faltante'}

ESTADÍSTICAS POR EXTENSIÓN
--------------------------"""

    # Agregar estadísticas de extensiones
    total_archivos = sum(extensiones.values())
    for ext, cantidad in list(extensiones.items())[:10]:  # Top 10
        porcentaje = (cantidad / total_archivos * 100) if total_archivos > 0 else 0
        reporte += f"\n{ext:<20} {cantidad:>4} archivos ({porcentaje:>5.1f}%)"
    
    reporte += f"""

TOTALES
-------
Total de archivos: {total_archivos}
Total de directorios: {len([d for r, d, f in os.walk('.') for dd in d if dd not in {'venv', '.git', '__pycache__'}])}

================================================================================
                           APLICACIONES DJANGO
================================================================================
"""

    if apps_django:
        reporte += "\nESTADO DE LAS APPS\n"
        reporte += "-" * 80 + "\n"
        reporte += f"{'App':<20} {'Estado':<10} {'Básicos':<10} {'Total':<10} {'Archivos Existentes':<30}\n"
        reporte += "-" * 80 + "\n"
        
        for app in apps_django:
            archivos_str = ", ".join(app["archivos_existentes"]) if app["archivos_existentes"] else "Ninguno"
            if len(archivos_str) > 25:
                archivos_str = archivos_str[:25] + "..."
            
            reporte += f"{app['nombre']:<20} {app['estado']:<10} {app['archivos_basicos']}/{app['total_basicos']:<8} {app['total_archivos']:<10} {archivos_str}\n"
        
        reporte += "\nDETALLE POR APP\n"
        reporte += "=" * 50 + "\n"
        
        for app in apps_django:
            reporte += f"\n📦 App: {app['nombre']}\n"
            reporte += f"   Ubicación: apps/{app['nombre']}/\n"
            reporte += f"   Estado: {app['estado']}\n"
            reporte += f"   Archivos básicos: {app['archivos_basicos']}/{app['total_basicos']}\n"
            
            if app["archivos_existentes"]:
                reporte += f"   Archivos encontrados: {', '.join(app['archivos_existentes'])}\n"
            else:
                reporte += "   ❌ No tiene archivos básicos\n"
    else:
        reporte += "\n❌ No se encontraron apps Django en el directorio 'apps/'\n"

    reporte += f"""

================================================================================
                         CONFIGURACIÓN DJANGO
================================================================================
"""

    if config_django["existe"]:
        reporte += "\n✅ ARCHIVO settings.py ENCONTRADO\n"
        reporte += "-" * 40 + "\n"
        
        configuraciones = {
            "INSTALLED_APPS": "Apps instaladas",
            "DATABASES": "Configuración de BD",
            "REST_FRAMEWORK": "API REST Framework",
            "STATIC_URL": "Archivos estáticos",
            "DEBUG": "Modo debug",
            "SECRET_KEY": "Clave secreta"
        }
        
        for config, descripcion in configuraciones.items():
            if config in config_django:
                estado = "✅ Configurado" if config_django[config] else "❌ Faltante"
                reporte += f"{config:<20} {estado:<15} {descripcion}\n"
        
        # Mostrar INSTALLED_APPS si existe
        if "INSTALLED_APPS_contenido" in config_django:
            reporte += f"\nCONTENIDO DE INSTALLED_APPS:\n"
            reporte += "-" * 40 + "\n"
            reporte += config_django["INSTALLED_APPS_contenido"]
            reporte += "\n"
    else:
        reporte += "\n❌ ARCHIVO settings.py NO ENCONTRADO\n"

    reporte += f"""

================================================================================
                         PAQUETES PYTHON
================================================================================

PAQUETES REQUERIDOS PARA SRI
----------------------------
"""

    for paquete, info in estado_paquetes.items():
        estado = "✅ Instalado" if info["instalado"] else "❌ Faltante"
        version_actual = info["version"] if info["instalado"] else "No instalado"
        reporte += f"{paquete:<25} {estado:<15} {version_actual:<15} (Req: {info['version_requerida']})\n"

    reporte += f"""

TODOS LOS PAQUETES INSTALADOS
-----------------------------
{chr(10).join(paquetes_instalados) if paquetes_instalados else 'No se pudieron obtener los paquetes instalados'}

================================================================================
                    ESTRUCTURA DE ALMACENAMIENTO SEGURO
================================================================================

DIRECTORIOS DE STORAGE
----------------------
storage/certificates/encrypted/     {verificar_archivo_existe('storage/certificates/encrypted')} Certificados .p12 encriptados
storage/certificates/temp/          {verificar_archivo_existe('storage/certificates/temp')} Temporal para procesamiento
storage/invoices/xml/               {verificar_archivo_existe('storage/invoices/xml')} Facturas XML firmadas
storage/invoices/pdf/               {verificar_archivo_existe('storage/invoices/pdf')} Facturas PDF generadas
storage/invoices/sent/              {verificar_archivo_existe('storage/invoices/sent')} Facturas enviadas al SRI
storage/logs/                       {verificar_archivo_existe('storage/logs')} Logs del sistema
storage/backups/                    {verificar_archivo_existe('storage/backups')} Respaldos de BD

================================================================================
                         ANÁLISIS Y PRÓXIMOS PASOS
================================================================================

ARCHIVOS FALTANTES CRÍTICOS
---------------------------"""

    archivos_criticos = ["requirements.txt", ".env", ".gitignore", "README.md"]
    archivos_faltantes = [archivo for archivo in archivos_criticos if not os.path.exists(archivo)]

    if archivos_faltantes:
        for archivo in archivos_faltantes:
            reporte += f"\n❌ {archivo}"
    else:
        reporte += "\n✅ Todos los archivos críticos están presentes"

    reporte += "\n\nAPPS DJANGO SIN CONFIGURAR\n"
    reporte += "-" * 30 + "\n"

    apps_sin_configurar = [app for app in apps_django if app["archivos_basicos"] == 0]
    if apps_sin_configurar:
        for app in apps_sin_configurar:
            reporte += f"❌ {app['nombre']} - Necesita archivos básicos\n"
    else:
        reporte += "✅ Todas las apps tienen al menos algunos archivos\n"

    reporte += """

TAREAS PRIORITARIAS
===================

1. CREAR ARCHIVOS DE CONFIGURACIÓN (CRÍTICO)
   
   Crear requirements.txt:
   -----------------------
   Django==4.2.7
   djangorestframework==3.14.0
   django-cors-headers==4.3.1
   psycopg2-binary==2.9.7
   celery==5.3.4
   redis==5.0.1
   cryptography==41.0.7
   lxml==4.9.3
   zeep==4.2.1
   reportlab==4.0.7
   Pillow==10.1.0
   python-decouple==3.8
   drf-spectacular==0.26.5

   Crear .env.example:
   -------------------
   DEBUG=True
   SECRET_KEY=django-insecure-change-this-key
   ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
   DB_NAME=vendo_sri_db
   DB_USER=vendo_sri_user
   DB_PASSWORD=vendo_sri_password
   DB_HOST=localhost
   DB_PORT=5432

2. INSTALAR DEPENDENCIAS
   pip install -r requirements.txt

3. CREAR ARCHIVOS BÁSICOS DE APPS
   Para cada app crear: models.py, views.py, urls.py, admin.py, apps.py

4. CONFIGURAR DJANGO
   - Actualizar INSTALLED_APPS en settings.py
   - Configurar base de datos
   - Aplicar migraciones: python manage.py makemigrations && python manage.py migrate

5. CREAR ESTRUCTURA COMPLETA
   - Crear .gitignore
   - Crear README.md
   - Configurar Docker (opcional)
   - Configurar tests

COMANDOS ÚTILES
===============
# Activar entorno virtual (Windows)
venv\\Scripts\\activate

# Instalar dependencias
pip install -r requirements.txt

# Aplicar migraciones
python manage.py makemigrations
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Ejecutar servidor
python manage.py runserver

# Regenerar esta documentación
python generar_documentacion.py

================================================================================
                                MÉTRICAS FINALES
================================================================================

PROGRESO DEL PROYECTO
---------------------
Estructura básica:       ✅ Completada (100%)
Configuración Django:    ⚠️  Parcial (30%)
Apps implementadas:      ❌ Pendiente (0%)
Documentación:           ⚠️  Iniciada (20%)

ESTADÍSTICAS GENERALES
---------------------
Total directorios:       {len([d for r, d, f in os.walk('.') for dd in d if dd not in {'venv', '.git', '__pycache__'}])}
Total archivos:          {total_archivos}
Apps Django:             {len(apps_django)}
Archivos Python:         {extensiones.get('.py', 0)}
Paquetes instalados:     {len(paquetes_instalados)}

================================================================================
Reporte generado automáticamente el {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Para actualizar, ejecuta: python generar_documentacion.py
================================================================================
"""

    # Guardar archivo
    try:
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            f.write(reporte)
        
        print(f"✅ DOCUMENTACIÓN GENERADA EXITOSAMENTE!")
        print(f"📄 Archivo creado: {nombre_archivo}")
        print(f"📊 Tamaño: {obtener_tamaño_archivo(nombre_archivo)}")
        print(f"📍 Ubicación: {os.path.abspath(nombre_archivo)}")
        
        # Preguntar si quiere ver el contenido
        respuesta = input("\n¿Quieres ver el contenido del archivo? (s/n): ")
        if respuesta.lower() in ['s', 'si', 'yes', 'y']:
            try:
                if os.name == 'nt':  # Windows
                    os.system(f'notepad {nombre_archivo}')
                else:  # Linux/Mac
                    os.system(f'cat {nombre_archivo}')
            except:
                print("No se pudo abrir automáticamente. Abre manualmente el archivo.")
        
        print(f"\n🎉 ¡Documentación completa lista!")
        return nombre_archivo
        
    except Exception as e:
        print(f"❌ Error al guardar el archivo: {str(e)}")
        return None

if __name__ == "__main__":
    print("🚀 GENERADOR DE DOCUMENTACIÓN - PROYECTO VENDO_SRI")
    print("=" * 60)
    
    try:
        archivo_generado = generar_reporte()
        if archivo_generado:
            print(f"\n📋 Para continuar con el proyecto, revisa las tareas prioritarias en: {archivo_generado}")
    except KeyboardInterrupt:
        print("\n❌ Operación cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        print("Asegúrate de estar en el directorio raíz del proyecto vendo_sri")