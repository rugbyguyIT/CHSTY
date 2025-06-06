import ssl
import requests
import json
import atexit
import wmi
import csv
import datetime
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

requests.packages.urllib3.disable_warnings()
ssl._create_default_https_context = ssl._create_unverified_context

def get_vcenter_vms(host, user, password):
    def collect_vms_from_folder(folder):
        local_vms = []
        for item in folder.childEntity:
            if isinstance(item, vim.Folder):
                local_vms.extend(collect_vms_from_folder(item))
            elif isinstance(item, vim.VirtualMachine):
                try:
                    used_space = sum([d.committed for d in item.storage.perDatastoreUsage]) / (1024 ** 3)
                    has_snapshot = hasattr(item, 'snapshot') and item.snapshot is not None
                except:
                    used_space = 0.0
                    has_snapshot = False
                local_vms.append({
                    'vm_name': item.name,
                    'host_name': item.runtime.host.name if item.runtime.host else 'Unknown',
                    'platform': 'vCenter',
                    'used_gb': round(used_space, 2),
                    'power_state': str(item.runtime.powerState),
                    'has_snapshot': has_snapshot
                })
            elif isinstance(item, vim.Datacenter):
                local_vms.extend(collect_vms_from_folder(item.vmFolder))
        return local_vms

    all_vms = []
    try:
        service_instance = SmartConnect(host=host, user=user, pwd=password)
        atexit.register(Disconnect, service_instance)
        content = service_instance.RetrieveContent()
        for dc in content.rootFolder.childEntity:
            if isinstance(dc, vim.Datacenter):
                all_vms.extend(collect_vms_from_folder(dc.vmFolder))
    except Exception as e:
        print(f"[vCenter] Error on {host}: {e}")
    return all_vms

def get_hyperv_vms(host, user, password):
    vms = []
    try:
        connection = wmi.WMI(computer=host, user=user, password=password, namespace="root\\virtualization\\v2")
        for vm in connection.Msvm_ComputerSystem():
            if vm.Caption == "Virtual Machine":
                settings = vm.associators(wmi_result_class="Msvm_VirtualSystemSettingData")[0]
                disks = settings.associators(wmi_result_class="Msvm_ResourceAllocationSettingData")
                used_bytes = 0
                for d in disks:
                    if "Hard Disk" in d.ElementName:
                        try:
                            used_bytes += int(d.VirtualQuantity) * 1024 ** 3
                        except:
                            continue
                vms.append({
                    'vm_name': vm.ElementName,
                    'host_name': host,
                    'platform': 'Hyper-V',
                    'used_gb': round(used_bytes / (1024 ** 3), 2),
                    'power_state': 'Running' if vm.EnabledState == 2 else 'Off',
                    'has_snapshot': "N/A"
                })
    except Exception as e:
        print(f"[Hyper-V] Error on {host}: {e}")
    return vms

def get_ahv_vms(cluster_ip, user, password):
    vms = []
    url = f"https://{cluster_ip}:9440/api/nutanix/v3/vms/list"
    headers = {"Content-Type": "application/json"}
    payload = {"kind": "vm"}

    try:
        response = requests.post(url, auth=(user, password), headers=headers, data=json.dumps(payload), verify=False)
        response.raise_for_status()
        vm_entities = response.json().get('entities', [])
        for vm in vm_entities:
            usage_bytes = vm.get('status', {}).get('resources', {}).get('disk_usage_bytes', 0)
            vms.append({
                'vm_name': vm['spec']['name'],
                'host_name': cluster_ip,
                'platform': 'AHV',
                'used_gb': round(usage_bytes / (1024 ** 3), 2),
                'power_state': vm['status']['resources'].get('power_state', 'UNKNOWN'),
                'has_snapshot': "N/A"
            })
    except Exception as e:
        print(f"[AHV] Error on {cluster_ip}: {e}")
    return vms

def prompt_platforms():
    print("\nSelect platforms to inventory:")
    print("1. VMware vCenter")
    print("2. Hyper-V")
    print("3. Nutanix AHV")
    print("Enter one or more numbers separated by commas (e.g., 1,3):")
    return set(i.strip() for i in input("Your selection: ").split(','))

def prompt_host_group(platform_name):
    hosts = input(f"\nEnter comma-separated {platform_name} hostnames or IPs: ").strip().split(',')
    user = input(f"Username for all {platform_name} hosts: ").strip()
    password = input(f"Password for all {platform_name} hosts: ").strip()
    return [{'host': h.strip(), 'user': user, 'password': password} for h in hosts if h.strip()]

def write_to_csv(vms, company_name):
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%I_%M%p")
    filename = f"{company_name}_vm_inventory_{timestamp}.csv"
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["vm_name", "host_name", "platform", "used_gb", "power_state", "has_snapshot"])
        writer.writeheader()
        for vm in vms:
            writer.writerow(vm)
    print(f"\nInventory written to: {filename}")

if __name__ == "__main__":
    company_name = input("Enter company name (used for output filename): ").strip().replace(" ", "_")
    selected = prompt_platforms()
    all_vms = []

    if '1' in selected:
        vcenter_hosts = prompt_host_group("vCenter")
        for info in vcenter_hosts:
            print(f"\nFetching VMs from vCenter host: {info['host']} ...")
            all_vms.extend(get_vcenter_vms(info['host'], info['user'], info['password']))

    if '2' in selected:
        hyperv_hosts = prompt_host_group("Hyper-V")
        for info in hyperv_hosts:
            print(f"\nFetching VMs from Hyper-V host: {info['host']} ...")
            all_vms.extend(get_hyperv_vms(info['host'], info['user'], info['password']))

    if '3' in selected:
        ahv_hosts = prompt_host_group("AHV")
        for info in ahv_hosts:
            print(f"\nFetching VMs from AHV cluster: {info['host']} ...")
            all_vms.extend(get_ahv_vms(info['host'], info['user'], info['password']))

    print(f"\nInventory complete. Found {len(all_vms)} VMs total.")
    write_to_csv(all_vms, company_name)
