import os
from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

app = Flask(__name__)

@app.route('/')
def index():
    # Obtenemos la lista de pacientes de la base de datos
    res = supabase.table("pacientes").select("*").execute()
    return render_template('index.html', pacientes=res.data)

@app.route('/subir', methods=['POST'])
def subir():
    nombre = request.form.get('nombre')
    archivo = request.files['foto']
    
    if archivo:
        # 1. Subir la imagen al "Bucket" llamado 'fotos'
        path = f"public/{archivo.filename}"
        supabase.storage.from_('fotos').upload(path, archivo.read(), {"content-type": archivo.content_type})
        
        # 2. Obtener la dirección (URL) de esa imagen
        url_imagen = supabase.storage.from_('fotos').get_public_url(path)
        
        # 3. Guardar en la tabla de datos
        supabase.table("pacientes").insert({
            "nombre": nombre, 
            "foto_url": url_imagen
        }).execute()
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)