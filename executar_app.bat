@echo off
echo === Analisador de Comentarios do YouTube com Gemini ===
echo.

REM Verificar se as dependências estão instaladas
python -c "import streamlit" 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Instalando dependencias...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo Falha ao instalar dependencias.
        pause
        exit /b 1
    )
)

echo.
echo Iniciando a aplicacao Streamlit...
echo.
streamlit run app.py

pause
