import sys
import json
import logging
import urllib3
import requests

from datetime import date
from config import list_url, list_data, vCenter_token, conf_token, conf_url

auth_url = {}
mass_vlan = {}
urllib3.disable_warnings()
logging.basicConfig(filename="sample_vc1.log", filemode="w", level=logging.INFO,
                    format='%(asctime)s %(levelname)s:%(message)s')


def create_file():
    with open("vm_info.json", "w") as new_file:
        ds = {'host': []}
        json.dump(ds, new_file, ensure_ascii=False, indent=4)
        new_file.close()


def create_session(auth_key=vCenter_token):
    header = {
        'Authorization': f'Basic {auth_key}'
    }

    for urls in list_url:
        r = requests.post(url=urls + "/api/session", headers=header, verify=False)

        if r.status_code == 201:
            logging.info(f"Сессия успешно создана! Ответ {r.reason}")
            session_id = r.json()
            ds = {urls: session_id}
            auth_url.update(ds)
        else:
            logging.error(f"Сессия не создалась вернулась ошибка: \n {r}")
            return sys.exit()


def gen_head(auth_key, urls):
    headers = {
        'Authorization': f'Basic {auth_key}',
        'vmware-api-session-id': auth_url.get(urls)
    }
    return headers


def get_all_vlan(auth_key=vCenter_token):
    for urls in list_url:
        headers = gen_head(auth_key, urls)

        resp = requests.get(url=f"{urls}/api/vcenter/network", headers=headers, verify=False)

        if resp.status_code == 200:
            logging.info(f"Вланы {list_data[urls]} - получены успешно {resp.reason}")
            r = resp.json()
        else:
            logging.error(f"Получена ошибка во время запроса VLAN у {list_data[urls]} - {resp}")
            sys.exit()

        for atr in r:
            ds = {atr['network']: atr['name']}
            mass_vlan.update(ds)


def get_vm(urls, auth_key=vCenter_token):
    headers = gen_head(auth_key, urls)

    resp = requests.get(url=urls + "/api/vcenter/vm", headers=headers, verify=False)

    if resp.status_code == 200:
        logging.info(f"Получил сервера успешно {resp.reason}")
        r = resp.json()
    else:
        logging.error(f"Ошибка получения списка серверов.")
        sys.exit()

    for reason in r:
        reason['location'] = list_data[urls]

    with open('vm_info.json', 'r') as vm_file:
        ds = json.load(vm_file)

    with open('vm_info.json', 'w') as nvm_file:
        ds['host'] += r
        json.dump(ds, nvm_file, ensure_ascii=False, indent=4)


def get_vm_info(urls, auth_key=vCenter_token):
    text = ""
    with open("vm_info.json", 'r') as nvm_data:
        vm_ds = json.load(nvm_data)
        headers = gen_head(auth_key, urls)

        for info_data in vm_ds['host']:
            if info_data['location'] == list_data[urls]:
                vm = info_data['vm']

                url1 = f'{urls}/api/vcenter/vm/{vm}/guest/networking/interfaces'
                url2 = f'{urls}/api/vcenter/vm/{vm}/guest/identity'
                url3 = f'{urls}/api/vcenter/vm/{vm}'

                resp1 = requests.get(url=url1, headers=headers, verify=False)
                resp2 = requests.get(url=url2, headers=headers, verify=False)
                resp3 = requests.get(url=url3, headers=headers, verify=False)

                r1 = resp1.json()
                r2 = resp2.json()
                reason = resp3.json()

                info_data['manufacturer'] = "VMware, Inc."

                try:
                    info_data['mac_address'] = r1[0]['mac_address']
                except KeyError:
                    logging.error(f"Не обнаружен Mac-Address станции - {vm}.")
                    info_data['mac_address'] = "Unknown"
                except Exception:
                    logging.error(f"При попытке получить Mac-Address станции - {vm}. Возникла ошибка.")
                    info_data['mac_address'] = "Unknown"

                try:
                    info_data['ip_address'] = r2['ip_address']
                except Exception:
                    logging.error(f"У станции {vm} - не возможно получить IP")
                    info_data['ip_address'] = "Unknown"

                try:
                    info_data['note_os'] = r2['full_name']['default_message']
                except Exception:
                    logging.error(f"У станции {vm} - не возможно получить OS")
                    info_data['note_os'] = "Unknown"

                try:
                    hdd_store = 0
                    for key1 in reason['disks'].keys():
                        try:
                            hdd_store += int(reason['disks'][key1]['capacity'])
                        except Exception:
                            logging.error(
                                f"У станции {vm} - не возможно получить Данные про диск {reason['disks'][key1]}")
                    info_data['hdd_store'] = round(int(hdd_store) / 1024**3)
                except Exception:
                    logging.error(f"Возникла ошибка при работе с данными - {info_data['vm']}")

                try:
                    if info_data['power_state'] == 'POWERED_ON':
                        info_data['power_state'] = "Running"
                    else:
                        info_data['power_state'] = "Unknown"
                except Exception:
                    info_data['power_state'] = "Unknown"

                info_data['network'] = {}

                step_vlan = 0
                for ks in list(reason['nics'].keys()):
                    try:
                        info_data['network'][f'vlan_{step_vlan}'] = mass_vlan[reason['nics'][ks]['backing']['network']]
                        step_vlan += 1
                    except Exception:
                        info_data['network'][f'vlan_{step_vlan}'] = reason['nics'][ks]['backing']['network']
                        step_vlan += 1

                # info_data['RAM'] = int(reason['memory']['size_MiB'])

                for symbol in (reason['identity']['bios_uuid'].replace('-', '')).replace('"', ''):
                    if len(text) in [2, 5, 8, 11, 14, 17, 20, 26, 29, 32, 35, 38, 41, 44]:
                        text += " " + symbol
                    elif len(text) == 23:
                        text += "-" + symbol
                    elif len(text) == 47:
                        break
                    else:
                        text += symbol

                info_data['s_n'] = f"VMware-{text}"

        with open("vm_info.json", "w") as cool_file:
            json.dump(vm_ds, cool_file, ensure_ascii=False, indent=4)


def send_file(auth_key=conf_token, urls=conf_url):
    today = date.today()

    head = {
        'Authorization': f'Basic {auth_key}',
        "X-Atlassian-Token": "nocheck",
    }

    files = {
        'file': ('vm_info.json', open("vm_info.json", 'rb')),
        'minorEdit': (None, 'true'),
        'comment': (None, f'{today.strftime("%d/%m/%Y")}'),
    }

    response = requests.post(urls, headers=head, files=files)
    if response.ok:
        logging.info(f"Файл отправлен успешно!")
    else:
        logging.critical(f"Файл, неотправлен!!! Ошибка: \n {response}")


if __name__ == "__main__":
    create_file()
    create_session()
    get_all_vlan()
    for link in list_url:
        get_vm(link)
        get_vm_info(link)
        logging.info(f"Обработка домена {link} - завершена")
    send_file()
