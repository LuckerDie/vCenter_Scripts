import os
from dotenv import load_dotenv

load_dotenv()

vCenter_token = os.getenv('VCENTER_TOKEN')
conf_token = os.getenv('CONF_TOKEN')
conf_url = os.getenv('CONF_URL')

vc1_url = os.getenv('VC1_URL')
vc2_url = os.getenv('VC2_URL')
vc3_url = os.getenv('VC3_URL')
vc4_url = os.getenv('VC4_URL')


list_url = [vc1_url, vc2_url, vc3_url, vc4_url]
list_data = {
    vc1_url: "DC1",
    vc2_url: "DC2",
    vc3_url: "DC3",
    vc4_url: "DC4"
}

