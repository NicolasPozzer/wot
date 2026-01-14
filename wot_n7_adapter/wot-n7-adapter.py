import subprocess
import re
import time
import os
import keyboard

interrumpir = False  # bandera global

ip_destino_wot = "92.223.0.0"  # Asegúrate de que esta IP sea la correcta para WOT
puerto = 5222
static_ip = "192.168.0.100"

proceso = 'wgc.exe'
proceso1 = 'WorldOfTanks.exe'

juego_name = 'WOTrule' # esto es solo para decoracion



def bloquear_conexion_adaptador_principal2(ip_destino, gateway_wot):
    """Bloquea la conexión del adaptador principal hacia la IP de destino de WOT."""
    try:
        # Eliminar cualquier ruta existente hacia la IP de destino
        cmd_delete = f'route delete {ip_destino}'
        subprocess.run(cmd_delete, shell=True, check=True)
        print(f"✅ Ruta hacia {ip_destino} eliminada del adaptador principal.")

        # Agregar una ruta específica para redirigir el tráfico hacia el adaptador de WOT
        cmd_add = f'route add {ip_destino} MASK 255.255.0.0 {gateway_wot} METRIC 50'
        subprocess.run(cmd_add, shell=True, check=True)
        print(f"✅ Ruta hacia {ip_destino} agregada a través del adaptador de WOT.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al modificar rutas: {e}")

def obtener_detalles_adaptador(nombre):
    """Obtiene IP, Gateway y Máscara de un adaptador específico."""
    try:
        cmd = f'netsh interface ipv4 show addresses "{nombre}"'
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding='utf-8', errors='replace')

        # Modificación: Captura tanto "Dirección IP" como "IP"
        ip_match = re.search(r"(?i)(?:Direcci[oó]n IP|IP)\s*:\s*([\d.]+)", result.stdout)
        ip = ip_match.group(1) if ip_match else None

        gateway_match = re.search(r"Puerta de enlace predeterminada\s*:\s*([\d.]+)", result.stdout)
        if not gateway_match:
            gateway_match = re.search(r"Puerta de enlace\s*:\s*([\d.]+)", result.stdout)
        if not gateway_match:
            gateway_match = re.search(r"Gateway\s*:\s*([\d.]+)", result.stdout)
        gateway = gateway_match.group(1) if gateway_match else None

        mask_match = re.search(r"m.?scara\s+([\d.]+)", result.stdout)
        mascara = mask_match.group(1) if mask_match else "255.255.255.0"

        return ip, gateway, mascara
    except Exception as e:
        print(f"⚠️ Error al obtener detalles para {nombre}: {str(e)}")
        return None, None, None



def obtener_adaptadores():
    """Obtiene los adaptadores de red usando netsh."""
    adaptadores = []
    print("\n🔹 Detectando adaptadores de red...")

    try:
        cmd = "netsh interface ipv4 show interfaces"
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding='utf-8', errors='replace')
        for line in result.stdout.splitlines():
            match = re.match(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\w+)\s+(.+)", line)
            if match:
                idx = match.group(1)
                estado = "✅ Conectado" if match.group(4) == "connected" else "❌ Sin conexión"
                nombre = match.group(5).strip()
                ip, gateway, mascara = obtener_detalles_adaptador(nombre)
                info = f"  [{len(adaptadores) + 1}] {nombre} - {estado}"
                if gateway:
                    info += f" | Gateway: {gateway}"
                if ip:
                    info += f" | IP: {ip}"
                else:
                    info += " | IP: None"
                adaptadores.append((idx, nombre, ip, gateway, mascara))
                print(info)
        return adaptadores
    except Exception as e:
        print(f"❌ Error al obtener adaptadores: {e}")
        return []


def resetear_a_dhcp(nombre):
    """Resetea el adaptador a DHCP borrando IP fija y DNS configurados."""
    try:
        cmd_ip = f'netsh interface ip set address name="{nombre}" dhcp'
        subprocess.run(cmd_ip, shell=True, check=True)
        cmd_dns = f'netsh interface ip set dns name="{nombre}" dhcp'
        subprocess.run(cmd_dns, shell=True, check=True)
        print(f"✅ {nombre} se ha reseteado a DHCP.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al resetear {nombre} a DHCP: {e}")


def configurar_ip_estatica(nombre, ip_estatica, mascara, gateway, dns):
    """
    Configura el adaptador con una IP estática, máscara, gateway y DNS.
    Se usa la métrica 50 para que el adaptador no sea tomado como principal para el tráfico general.
    Ejecuta:
      netsh interface ip set address name="{nombre}" static {ip_estatica} {mascara} {gateway} 50
      netsh interface ip set dns name="{nombre}" static {dns} primary
    """
    try:
        cmd_ip = f'netsh interface ip set address name="{nombre}" static {ip_estatica} {mascara} {gateway} 50'
        subprocess.run(cmd_ip, shell=True, check=True)
        print(f"✅ Se asignó IP estática {ip_estatica} con máscara {mascara} y gateway {gateway} en {nombre}")

        cmd_dns = f'netsh interface ip set dns name="{nombre}" static {dns} primary'
        subprocess.run(cmd_dns, shell=True, check=True)
        print(f"✅ Se asignó DNS {dns} en {nombre}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al configurar IP estática en {nombre}: {e}")


def asignar_metrica(nombre, metric):
    """Asigna una métrica específica al adaptador."""
    try:
        cmd = f'netsh interface ipv4 set interface name="{nombre}" metric={metric}'
        subprocess.run(cmd, shell=True, check=True)
        print(f"✅ Se asignó la métrica {metric} a {nombre}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al asignar la métrica en {nombre}: {e}")


def eliminar_ruta(network_target):
    """Elimina cualquier ruta existente para el destino especificado."""
    try:
        cmd = f'route delete {network_target}'
        subprocess.run(cmd, shell=True, check=True)
        print(f"✅ Ruta {network_target} eliminada.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al eliminar ruta {network_target}: {e}")


def modificar_ruta(accion, gateway, network_target):
    """Modifica la ruta específica para World of Tanks de forma persistente."""
    # Usar el parámetro -p para hacerla persistente
    if accion.lower() == 'add':
        comando = f'route -p add {network_target} MASK 255.255.0.0 {gateway} METRIC 50'
    elif accion.lower() == 'delete':
        comando = f'route -p delete {network_target}'
    else:
        print("Acción no válida")
        return
    subprocess.run(comando, shell=True, check=True)



def verificar_proceso(proceso):
    cmd = f'tasklist /FI "IMAGENAME eq {proceso}"'
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding='utf-8', errors='replace')
    return proceso.lower() in result.stdout.lower()



# Definir los colores para la consola
ROJO = '\033[91m'
VERDE = '\033[92m'
AMARILLO = '\033[93m'
RESET = '\033[0m'

def obtener_ip_local_conectada(puerto, ip_excluir):
    """Obtiene la IP local conectada al servidor de WOT en el puerto especificado, excluyendo una IP no deseada."""
    try:
        cmd = f'netstat -n | findstr :{puerto} | findstr /V "{ip_excluir}"'
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding='utf-8', errors='replace')

        for line in result.stdout.splitlines():
            if 'ESTABLISHED' in line:
                ip_local = line.split()[1].split(':')[0]  # Extraer IP local de la conexión
                return ip_local
        return None
    except Exception as e:
        print(f"⚠️ Error al obtener la IP local conectada: {str(e)}")
        return None

def monitorearre_conexion(gateway_wot, ip_wot, ip_excluir):
    """Monitorea la conexión asegurando que se use la IP correcta para WOT y excluyendo la IP incorrecta."""
    try:
        while True:
            # Limpiar la consola
            os.system('cls' if os.name == 'nt' else 'clear')

            ip_local = obtener_ip_local_conectada(puerto, ip_excluir)
            if ip_local:
                print(f"🔍 IP local conectada al servidor de WOT: {ip_local}")
                print(f"🔍 IP Red sin Microcortes! (la que deberías usar) {ip_wot}")

                if ip_local == ip_wot:
                    print(f"{VERDE}✅ WOT está conectado correctamente con la IP adecuada.{RESET}")
                else:
                    print(f"{ROJO}⚠️ Advertencia: WOT está usando otra IP ({ip_local}).{RESET}")
            else:
                print(f"{AMARILLO}⚠️ No se encontró una conexión activa en el puerto {puerto}.{RESET}")

            time.sleep(5)
    except KeyboardInterrupt:
        print("\n🔧 Monitoreo detenido manualmente.")

import threading

def esperar_tecla():
    global interrumpir
    while not interrumpir:
        tecla = input().strip().lower()
        if tecla == "z":
            print("\n🟥 Tecla `z` detectada desde la terminal. Deteniendo monitoreo...")
            interrumpir = True

def monitorear_conexion(gateway_wot, ip_wot, ip_excluir):
    global interrumpir
    interrumpir = False

    print("\n🟡 Escribe `z` y presiona Enter para detener la monitorización.")

    # Hilo para leer la tecla en la terminal
    threading.Thread(target=esperar_tecla, daemon=True).start()

    try:
        while not interrumpir:
            os.system('cls' if os.name == 'nt' else 'clear')

            ip_local = obtener_ip_local_conectada(puerto, ip_excluir)
            if ip_local:
                print(f"🔍 IP local conectada al servidor de {juego_name}: {ip_local}")
                print(f"🔍 IP Red sin Microcortes! (la que deberías usar) {ip_wot}")

                if es_tethering_iphone(ip_wot):
                    print(f"{VERDE}✅ WOT usando tethering iPhone correctamente.{RESET}")
                    print("\n🟥 Tecla `z` y Enter Rapido! Si desea parar la conexion")
                elif ip_local == ip_wot:
                    print(f"{VERDE}✅ WOT está conectado correctamente con la IP adecuada.{RESET}")
                    print("\n🟥 Tecla `z` y Enter Rapido! Si desea parar la conexion")
                else:
                    print(f"{ROJO}⚠️ Advertencia: {juego_name} está usando otra IP ({ip_local}).{RESET}")

                    print("\n🟥 Tecla `z` y Enter Rapido! Si desea parar la conexion")
            else:
                print(f"{AMARILLO}⚠️ No se encontró una conexión activa en el puerto {puerto}.{RESET}")
                print("\n🟥 Tecla `z` y Enter Rapido! Si desea parar la conexion")

            time.sleep(5)

    except Exception as e:
        print(f"⚠️ Error durante la monitorización: {str(e)}")


def bloquear_conexion_adaptador_principal(local_ip):
    """
    Bloquea el tráfico saliente en el puerto 5222 del adaptador principal usando su IP local.
    Esto fuerza que las conexiones hacia WOT se establezcan desde el adaptador secundario.
    """
    try:
        cmd = f'netsh advfirewall firewall add rule name="{juego_name}" dir=out localip={local_ip} protocol=TCP localport={puerto} action=block'
        subprocess.run(cmd, shell=True, check=True)
        print(f"✅ Se bloqueó el puerto {puerto} para la IP {local_ip} en el adaptador principal.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al aplicar la regla de firewall: {e}")

def desbloquear_conexion_adaptador_principal():
    """Elimina la regla de firewall para el puerto 5222."""
    try:
        cmd = f'netsh advfirewall firewall delete rule name="{juego_name}"'
        subprocess.run(cmd, shell=True, check=True)
        print("✅ Regla de firewall eliminada.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al eliminar la regla de firewall: {e}")

def es_tethering_iphone(ip):
    return ip is not None and ip.startswith("172.20.10.")


def main():
    adaptadores = obtener_adaptadores()
    if not adaptadores:
        print("❌ No se encontraron adaptadores válidos")
        return

    try:
        # Adaptador principal
        seleccion_principal = int(
            input("\nSelecciona el adaptador principal (para Internet, youtube, twitch, etc), por número: ").strip()
        ) - 1

        idx_principal, nombre_principal, ip_principal, gateway_principal, mascara_principal = adaptadores[seleccion_principal]

        if not gateway_principal:
            print(f"❌ El adaptador {nombre_principal} no tiene gateway")
            return

        print(f"\n Adaptador principal: {nombre_principal} | IP: {ip_principal} | GW: {gateway_principal}")

        # Adaptador WOT
        seleccion_wot = int(
            input(f"\nSelecciona el adaptador para {juego_name}, por numero: ").strip()
        ) - 1

        idx_wot, nombre_wot, ip_wot, gateway_wot, mascara_wot = adaptadores[seleccion_wot]

        if not gateway_wot:
            print(f"❌ El adaptador {nombre_wot} no tiene gateway")
            return

        print(f"\n🎮 Adaptador WOT: {nombre_wot} | IP: {ip_wot} | GW: {gateway_wot}")

    except (ValueError, IndexError):
        print("❌ Selección inválida")
        return

    #  Bloqueo del adaptador principal
    if ip_principal:
        bloquear_conexion_adaptador_principal(ip_principal)
    else:
        print("❌ No se pudo bloquear el adaptador principal")
        return

    # 🔄 Reset DHCP en adaptador WOT
    print(f"\n Reseteando {nombre_wot} a DHCP...")
    resetear_a_dhcp(nombre_wot)
    time.sleep(8)

    ip_wot_nueva, gateway_wot_nueva, mascara_wot_nueva = obtener_detalles_adaptador(nombre_wot)
    if not gateway_wot_nueva:
        print(f"❌ No se pudo obtener gateway para {nombre_wot}")
        return

    print(f"\n🌐 Configuración WOT actualizada:")
    print(f"   IP: {ip_wot_nueva}")
    print(f"   Gateway: {gateway_wot_nueva}")
    print(f"   Máscara: {mascara_wot_nueva}")

    #  Detectar iPhone
    es_iphone = es_tethering_iphone(ip_wot_nueva)

    if es_iphone:
        print("\n iPhone detectado → modo DHCP puro (SIN IP estática)")
        ip_wot = ip_wot_nueva

    else:
        print("\n Android detectado → modo IP estática")

        octetos = gateway_wot_nueva.split('.')
        ip_estatica = f"{octetos[0]}.{octetos[1]}.{octetos[2]}.100"

        print(f"🔄 Asignando IP estática {ip_estatica}")
        configurar_ip_estatica(
            nombre_wot,
            ip_estatica,
            mascara_wot_nueva,
            gateway_wot_nueva,
            "8.8.8.8"
        )

        asignar_metrica(nombre_wot, 50)
        ip_wot = ip_estatica

    # 🚧 Rutas
    eliminar_ruta(ip_destino_wot)
    bloquear_conexion_adaptador_principal2(ip_destino_wot, gateway_wot_nueva)

    try:
        # ⏳ Esperar WOT
        while not (verificar_proceso(proceso) or verificar_proceso(proceso1)):
            print(f"⏳ Esperando {proceso} / {proceso1}...")
            time.sleep(5)

        modificar_ruta('ADD', gateway_wot_nueva, ip_destino_wot)

        print(f"\n✅ Ruta para {juego_name} aplicada correctamente")
        print("🔍 Monitoreando conexión...\n")

        monitorear_conexion(gateway_wot_nueva, ip_wot, ip_principal)

    except subprocess.CalledProcessError as e:
        print(f"❌ Error de red: {e}")

    finally:
        modificar_ruta('DELETE', gateway_wot_nueva, ip_destino_wot)
        desbloquear_conexion_adaptador_principal()


if __name__ == "__main__":
    while True:
        main()
        respuesta = input("\n🔁 ¿Querés reiniciar todo el proceso? (s/n): ").strip().lower()
        if respuesta != "s":
            print("👋 Saliendo del programa.")
            break