# Usamos la imagen oficial de Jupyter con PySpark
FROM jupyter/pyspark-notebook:latest

# Cambiar a root temporalmente para crear carpetas
USER root

# Crear directorio de trabajo
WORKDIR /home/jovyan/work

# Copiar el archivo de requirements
COPY requirements.txt .

# Instalar dependencias extra (Delta Lake, Faker, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# Configurar el script de inicio de IPython para inicializar Spark con Delta
RUN mkdir -p /home/jovyan/.ipython/profile_default/startup/
COPY scripts/00-spark-setup.py /home/jovyan/.ipython/profile_default/startup/

# Ajustar permisos
RUN chown -R jovyan:users /home/jovyan/.ipython

# Volver al usuario jovyan por seguridad
USER jovyan

# Copiar el proyecto al contenedor (aunque en dev usaremos un volume)
COPY . /home/jovyan/work/

# Exponer el puerto de JupyterLab
EXPOSE 8888

# Comando por defecto para arrancar JupyterLab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token='aml_token'"]
