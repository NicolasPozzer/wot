@echo off
setlocal enabledelayedexpansion

cls
echo ================================
echo LISTA DE ADAPTADORES DE RED
echo ================================

set /a count=0
for /f "skip=3 tokens=1,2,3,4,*" %%A in ('netsh interface ipv4 show interfaces') do (
    set /a count+=1
    set "idx=%%A"
    set "mtu=%%B"
    set "metrica=%%C"
    set "estado=%%D"
    set "nombre=%%E"

    rem Solo mostramos si tiene nombre valido
    if not "!nombre!"=="" (
        echo [!count!] !nombre! - Estado: !estado!
        set "adapter[!count!]=!nombre!"
    )
)

if !count! EQU 0 (
    echo ❌ No se encontraron adaptadores.
    pause
    exit /b
)

set /p selected=Seleccione un adaptador por numero para restaurarlo a DHCP: 
set "adapterName=!adapter[%selected%]!"

if not defined adapterName (
    echo ❌ Selección inválida.
    pause
    exit /b
)

echo ================================
echo 🔄 Restaurando "!adapterName!" a DHCP...
echo ================================

netsh interface ip set address name="!adapterName!" dhcp
netsh interface ip set dns name="!adapterName!" dhcp

echo ✅ El adaptador "!adapterName!" fue restaurado a DHCP.
pause
3