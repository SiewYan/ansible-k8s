# Deployment of a Kubernetes cluster via ansible

## Overview
The provided playbooks Ansible deploy a Kubernetes cluster with a basic topology: one master and at least two nodes.
The installation is based on the kubeadm tool configured with a pre-generated admin token and flannel network.
The playbooks enrich the cluster installation with a set of services such as:
- dashboards: legacy and Grafana
- monitoring: Prometheus Operator
- Big Data: Spark Operator.

## System requirements
- Deployment environment must have Ansible 2.4.0+
- Expects 3 Ubuntu nodes (tested on 18.04)
- Master and nodes must have passwordless SSH access

## Get Started
This section represents a quick installation and is not intended to teach you about all the components. The easiest way to get started is to clone the 'ansible-k8s' repository:

```
# git clone https://github.com/zangrand/ansible-k8s.git
# cd ansible-k8s
```

The directory structure should be like

```
ansible-k8s/
├── group_vars
│   └── all
├── inventory
├── k8s
│   ├── alertmanager-service.yaml
│   ├── grafana-service.yaml
│   ├── dashboard-setup.yaml
│   └── prometheus-service.yaml
├── README.md
├── roles
│   ├── common
│   │   └── tasks
│   │       └── main.yml
│   ├── docker
│   │   └── tasks
│   │       └── main.yml
│   ├── kubeadm
│   │   └── tasks
│   │       └── main.yml
│   ├── master
│   │   └── tasks
│   │       └── main.yml
│   └── node
│       └── tasks
│           └── main.yml
└── deploy_k8s.yaml
```

Now edit the inventory file properly by specifying the IP addresses of master and nodes:

```
[master]
master1 ansible_host=10.64.41.16

[node]
node1 ansible_host=10.64.41.11
node2 ansible_host=10.64.41.12
node3 ansible_host=10.64.41.15
...
```

Add your SSH key to the ssh-agent

```
# eval "$(ssh-agent -s)"
Agent pid 59566

# ssh-add ~/.ssh/id_rsa
```
or
```
# ssh-add ~/your_cert.pem
```

Finally execute:

```
# ansible-playbook -i inventory deploy_k8s.yaml
```

## Test if it worked
The cluster exposes the following services:
- K8S dashboard: https://<master_ip>:30900
- Prometheus UI: http://<master_ip>:30901
- Alertmanager UI: http://<master_ip>:30902
- Grafana UI: http://<master_ip>:30903

To login into the K8S dashboard use the token of the kube-system:default service account. To get it, execute the following command at the master node:

```
# kubectl -n kube-system describe secret kubernetes-dashboard
...
Data
====
ca.crt:     1025 bytes
namespace:  11 bytes
token:      eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJrdWJlcm5ldGVzLWRhc2hib2FyZC10b2tlbi05cGc5NyIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50Lm5hbWUiOiJrdWJlcm5ldGVzLWRhc2hib2FyZCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6IjAyYjYzZGRkLWFhYzItMTFlOC1iNTBkLWZhMTYzZTQ2OWU0ZiIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDprdWJlLXN5c3RlbTprdWJlcm5ldGVzLWRhc2hib2FyZCJ9.XPSzu31SvkR_xwfd3MpLQBkHc7anZlEA1FMSMrZsU6wENflLJQEPrEUJmYji24jU4vTnd2eVK1rhEB4P1iPEiVg0nCZIIhkJTtpaNTyefV1Uq3V9JUTxEO9rMAsfSx16yqctuSi9qgUU7Ac85ZEffJqrKrQwSkQGyCnrDuAQ11Ryl5VGWbTfTfeEP-epjm0jnAcI1akhkoS2xUESRV9Bq41rOtboJYv3hAe0pjOL7CHZ3mTsHMHXR_0IDQvCTx8tC9S_vU09-jK8c_4UAkoUDd5-_1DPl68AckAMtgZyPSQLKnlFW50WwQt5WCwp7VGrBL_okM-E7QeTQkrUMrGTDw
```

To login into the Grafana dashboard as administrator use the credential: username=admin and password=admin. The first login requires the changing of the default password for security reasons.




