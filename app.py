import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

app = Flask(__name__)
# Necesitamos una clave secreta para poder usar mensajes Flash
app.secret_key = "evolucion_chile_secret_key"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ingresar')
def ingresar():
    return render_template('ingresar.html')

@app.route('/guardar_paciente', methods=['POST'])
def guardar_paciente():
    form_data = request.form.to_dict()
    datos = {k: v.upper() if isinstance(v, str) else v for k, v in form_data.items()}
    
    rut = datos.get('numero_documento_paciente', 'SIN_RUT').replace('.', '').strip()
    sede = datos.get('sede', 'SIN_SEDE').replace(' ', '_')
    
    # 1. VALIDACIÓN PREVIA EN LA BASE DE DATOS (Evita subir archivos en balde si está duplicado)
    try:
        existe = supabase.table("pacientes").select("id").eq("numero_documento_paciente", rut).execute()
        if existe.data:
            flash(f"EL RUT {rut} YA SE ENCUENTRA REGISTRADO EN EL SISTEMA", "error")
            return redirect(url_for('ingresar'))
    except Exception as e:
        print(f"Error al verificar duplicado: {e}")

    # 2. PROCESO DE ALMACENAMIENTO JERÁRQUICO EN LA NUBE
    archivo = request.files.get('imagen_documento_identidad')
    if archivo and archivo.filename != '':
        try:
            extension = os.path.splitext(archivo.filename)[1].lower()
            nombre_cedula = f"CEDULA_{rut}{extension}"
            ruta_cloud = f"{sede}/USUARIOS/{rut}/CEDULAS/{nombre_cedula}"
            
            supabase.storage.from_('fotos').upload(
                path=ruta_cloud, 
                file=archivo.read(), 
                file_options={"content-type": archivo.content_type, "upsert": "true"}
            )
            
            url_publica = supabase.storage.from_('fotos').get_public_url(ruta_cloud)
            datos['imagen_documento_identidad'] = url_publica
            
        except Exception as e:
            print(f"Error al subir el archivo al Storage: {e}")

    # 3. INSERCIÓN FINAL EN LA BASE DE DATOS
    try:
        supabase.table("pacientes").insert(datos).execute()
        flash("PACIENTE REGISTRADO EXITOSAMENTE", "success")
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error Supabase DB: {e}")
        flash("OCURRIÓ UN ERROR AL INTENTAR GUARDAR EN LA BASE DE DATOS", "error")
        return redirect(url_for('ingresar'))


@app.route('/ver_ficha')
def ver_ficha():
    return render_template('ver_ficha.html')

@app.route('/buscar_pacientes')
def buscar_pacientes():
    query = request.args.get('q', '').upper()
    try:
        res = supabase.table("pacientes").select("id, sede, numero_documento_paciente, nombre_completo_paciente") \
            .or_(f"numero_documento_paciente.ilike.%{query}%,nombre_completo_paciente.ilike.%{query}%") \
            .execute()
        return jsonify({"pacientes": res.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/obtener_paciente/<int:id_paciente>')
def obtener_paciente(id_paciente):
    res = supabase.table("pacientes").select("*").eq("id", id_paciente).single().execute()
    return jsonify(res.data)

@app.route('/verificar_rut/<rut>')
def verificar_rut(rut):
    try:
        # Buscamos si ya existe el RUT en Supabase
        res = supabase.table("pacientes").select("id").eq("numero_documento_paciente", rut.upper()).execute()
        if res.data:
            return jsonify({"existe": True})
        return jsonify({"existe": False})
    except Exception as e:
        print(f"Error al verificar RUT: {e}")
        return jsonify({"existe": False}), 500

@app.route('/modificar')
def modificar():
    return render_template('modificar.html')

@app.route('/actualizar_paciente/<int:id_paciente>', methods=['POST'])
def actualizar_paciente(id_paciente):
    form_data = request.form.to_dict()
    
    # 1. Estandarizamos a MAYÚSCULAS y limpiamos espacios de los textos
    datos = {}
    for k, v in form_data.items():
        if isinstance(v, str):
            valor_limpio = v.strip()
            # Si el campo está vacío, lo transformamos en None (null para Supabase)
            if valor_limpio == "":
                datos[k] = None
            else:
                datos[k] = valor_limpio.upper()
        else:
            datos[k] = v

    # 2. Intentamos guardar la actualización corregida en Supabase
    try:
        supabase.table("pacientes").update(datos).eq("id", id_paciente).execute()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error al actualizar en Supabase: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/eliminar')
def eliminar():
    return render_template('eliminar.html')

@app.route('/eliminar_paciente/<int:id_paciente>', methods=['DELETE'])
def eliminar_paciente(id_paciente):
    try:
        # Eliminamos el registro directamente en Supabase usando el ID único
        supabase.table("pacientes").delete().eq("id", id_paciente).execute()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error al eliminar paciente: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)