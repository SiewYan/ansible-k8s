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
- Expects 3 Ubuntu nodes (test on 18.04)
- Master and nodes must have passwordless SSH access

## Get Started
This section represents a quick installation and is not intended to teach you about all the components. The easiest way to get started is to clone the 'ansible-k8s' repository:

```
git clone https://github.com/zangrand/ansible-k8s.git
cd ansible-k8s
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
│   ├── kubernetes-dashboard.yaml
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
│   │   ├── handlers
│   │   │   └── main.yml
│   │   └── tasks
│   │       └── main.yml
│   └── node
│       └── tasks
│           └── main.yml
└── site.yml
```

Now edit the inventory file properly by specifying the IP addresses of master and nodes:

```
[master]
master1 ansible_host=10.64.41.16

[node]
10.64.41.11
10.64.41.12
10.64.41.15
...
```

Add your SSH key to the ssh-agent

```
$ eval "$(ssh-agent -s)"

$ ssh-add ~/.ssh/id_rsa
```
or
```
$ ssh-add ~/your_cert.pem
```

Finally execute:

```
$ ansible-playbook -i inventory site.yml
```

## Test if it worked
The cluster exposes the following services:
- K8S dashboard: https://<master_ip>:30900
- Prometheus UI: http://<master_ip>:30901
- Alertmanager UI: http://<master_ip>:30902
- Grafana UI: http://<master_ip>:30903

