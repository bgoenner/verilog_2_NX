
import os, sys

import regex
import re
import mmap

import networkx as nx
import matplotlib.pyplot as plt

#module_reg = r"\s*module\s*(?P<module>\s*[a-zA-Z][\w]*)\s*\((?P<ports>[\s*\w*,]*)\)\s*;(?P<module_netlist>[\w*\s*,;\(\)\.]*?)endmodule"
module_reg = r"^[ ]*module\s*(?P<module_name>[a-zA-Z][\w]*)\s\((?P<module_ports>[\s\w,]*)\)\s*;(?P<module_netlist>[\s\w.,\(\);\/]*?)endmodule"
input_reg  = r"^[ ]*input\s*(?P<input_port>[\w*, \n]*);"
output_reg = r"^[ ]*output\s*(?P<output_port>[\w*, \n]*);"
wire_reg   = r"^[ ]*wire\s*(?P<wires>[\w*, \n]*);"
comp_reg   = r"^[ ]*(?P<component>[a-zA-Z][\w]*)\s*(?P<name>[a-zA-Z][\w]*)\s*\((?P<ports>[\w\(\),\s.]*)\)\s*;"
net_reg = r"^[ ]*(module\s*(?P<module_name>[a-zA-Z][\w]*)\s*\((?P<module_ports>[\s\w,]*\);)|wire\s*(?P<wires>[a-zA-Z][\w\s,]*);|input\s*(?P<in_ports>[a-zA-Z][\w\s,]*);|output\s*(?P<out_ports>[a-zA-Z][\w\s,]*);|(?P<component>[a-zA-Z][\w]*)\s*(?P<name>[a-zA-Z][\w]*)\s*\((?P<ports>[\w\(\),\s.]*)\)\s*;)"
component_port_reg = r".(?P<component_port>[a-zA-Z][\w]*)\s*\(\s*(?P<net_port>[a-zA-Z][\w]*)\s*\)\s*"

m_frm = 'utf-8'
"""
in_v input verilog file
"""
def get_modules(in_v, debug=False):

    # get modules
    mod_re_b = bytes(module_reg, 'utf-8')

    with open(in_v, 'r+') as f:
        data = mmap.mmap(f.fileno(), 0)
        mo = regex.finditer(mod_re_b, data, re.MULTILINE)

    mod_names= {}
    mod_nets = {}

    mod_graphs = {} # place for nx graph mod_name : {'netlist':Graph()}

    # get module names
    for m in mo:
        mod_nets[m.group('module_name').decode('utf-8')] = {
            'ports':{},
            'wires':[],
            'components':{}
        }
        mod_names[m.group('module_name').decode('utf-8')] = {'isSubmodule':False} 

        mod_graphs[m.group('module_name').decode('utf-8')] = {
                'netlist':nx.Graph(),
                'inputs':[],
                'outputs':[],
                'wires':[]}

    with open(in_v, 'r+') as f:
        data = mmap.mmap(f.fileno(), 0)
        mo = regex.finditer(mod_re_b, data, re.MULTILINE)

    for m in mo:
        mod_name = m.group('module_name').decode('utf-8')
        # remove ws and split by ,
        mod_ports = regex.sub(r'\s', '', m.group('module_ports').decode('utf-8')).split(',')
        
        # build out netlist
        mod_parsed_net = parse_net(m.group('module_netlist'), mod_names=mod_names, mod_graph=mod_graphs[mod_name]['netlist'])
        print(mod_parsed_net)
    
        for p in mod_ports:
            if p in mod_parsed_net['inputs']:
                mod_net[mod_name]['ports'][p] = 'input'
                mod_graph[mod_name]['inputs'].append(p)
            elif p in mod_parsed_net['outputs']:
                mod_net[mod_name]['ports'][p] = 'output'
                mod_graph[mod_name]['outputs'].append(p)

        mod_nets[mod_name]['wires'] = mod_parsed_net['wires']
        mod_nets[mod_name]['components'] = mod_parsed_net['components']

    top_module = None
    for m in mod_names:
        if mod_names[m]['isSubmodule']:
            if top_module is None:
                top_module = m
            else:
                raise ValueError("More than one top module")
        else:
            continue
 
    for G_el in mod_graphs:
        print(G_el)
        G = mod_graphs[G_el]['netlist']
        #subax1 = plt.subplot(121)
        nx.draw(G, with_labels=True, font_weight='bold')
        #subax2 = plt.subplot(122)
        #nx.draw_shell(G, nlist=[range(5, 10), range(5)], with_labels=True, font_weight='bold')
        plt.show()

def parse_net(in_net, mod_names=None, mod_graph=None, debug=False):

    net_re_b = bytes(net_reg, 'utf-8')

    if isinstance(in_net, bytes):
        values = regex.finditer(net_re_b, in_net, re.MULTILINE)
    else:
        ValueError("in_net not bytes")

    net_dict = {
        'inputs':[],
        'outputs':[],
        'wires':[],
        'components':{}
    }

    for v in values:
        v_str = v.groups()[0].decode('utf-8')
        print(v_str)
        ports = []
        key = regex.match(r'\w*', v_str)[0]
        print(key)
        if key == 'input':
            ports = regex.sub(bytes(r'[\s;]','utf-8'),bytes('','utf-8'), v.group('in_ports'))
            ports = ports.decode('utf-8').split(',')
            net_dict['inputs'].append(ports)
            mod_graph.add_nodes_from([(x, {'node_type':'input'}) for x in ports])
        elif key == 'output':
            ports = regex.sub(bytes(r'[\s;]','utf-8'),bytes('','utf-8'), v.group('out_ports'))
            ports = ports.decode('utf-8').split(',')
            net_dict['outputs'].append(ports)
            mod_graph.add_nodes_from([(x, {'node_type':'output'}) for x in ports])
        elif key == 'wire':
            connections = regex.sub(bytes(r'[\s;]','utf-8'),bytes('','utf-8'), v.group('wires'))
            connections = connections.decode('utf-8').split(',')
            net_dict['wires'].append(connections)
            mod_graph.add_nodes_from([(x, {'node_type':'wire'}) for x in connections])
        else: # component
            cv = regex.match(comp_reg, v_str)
            cp = regex.finditer(component_port_reg, cv.group('ports'), re.MULTILINE) 
            net_dict['components'][cv.group('name')] =  {
                'component_type':cv.group('component'),
                'ports':{}
            }
            mod_graph.add_node(cv.group('name'), node_type=cv.group('component'))
            for p in cp:
                net_dict['components'][cv.group('name')]['ports'] = {
                    'comp_port':p.group('component_port'),
                    'net_port':p.group('net_port')
                }
                mod_graph.add_edge(cv.group('name'),p.group('net_port'), port=p.group('component_port'))
            if mod_names is not None:
                if cv.group('name') in mod_names:
                    mod_names[cv.group('name')] = True
                    net_dict['components'][cv.group('name')]['isModule'] = True
                else:
                    net_dict['components'][cv.group('name')]['isModule'] = False

    return net_dict

def main(in_v, out_dir):
    pass

