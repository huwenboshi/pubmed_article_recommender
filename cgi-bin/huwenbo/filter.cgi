#!/usr/bin/python -u

import xml.etree.ElementTree as ET
import urllib2
import cgitb
import time
import cgi
import sys
import codecs
import os

from consts import *
from db_utils import *
from filter_utils import *

sys.path.append('./httpagentparser-1.5.1')
import httpagentparser

sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
cgitb.enable()

con = connect_db(db_loc)

########################### HTTP HTML HEADER ###################################

# print http_header and html header
user_agent = os.environ.get("HTTP_USER_AGENT", "N/A")
os_browser = httpagentparser.simple_detect(user_agent)
browser = os_browser[1]
if(browser.lower().find('safari') >= 0):
    print http_header_mac
else:
    print http_header
print """
<!DOCTYPE html>
<html>
    <head>
        <title>
            PubMed Miner - Gene Filter Result
        </title>
        <style type="text/css">
            #summary_tbl {
                border-bottom: 1px Solid Black;         
                border-right: 1px Solid Black;         
                border-collapse : collapse;  
            }
            #summary_tbl td, #summary_tbl th {    
                border-left: 1px Solid Black;         
                border-top: 1px Solid Black;              
                border-bottom: 1px Solid Black;    
                border-right:none;  
            }
            #user_input_form {
                display: none;
            }
        </style>
        <link rel="stylesheet" 
            href="../../huwenbo/table_sorter/themes/blue/style.css" />
        <script type="text/javascript"
                src="../../huwenbo/table_sorter/jquery-latest.js">
        </script>
        <script type="text/javascript"
                src="../../huwenbo/table_sorter/jquery.tablesorter.js">
        </script>
        <script type="text/javascript">
            $(document).ready(function(){
            
                ///////// table sorter for ewas gene /////////
                $.tablesorter.addParser({
                    id: 'ewas_gene_exp_pval',
                    is: function(s) {
                        return false;
                    },
                    format: function(text, table, cell) {
                        return parseFloat(text);
                    },
                    type: 'numeric'
                });
                $('#ewas_gene_exp_tbl').tablesorter({
                    headers: {
                        4: {
                            sorter: 'ewas_gene_exp_pval'
                        }
                    }
                });
                
                ///////// table sorter for ewas prot /////////
                $.tablesorter.addParser({
                    id: 'ewas_prot_exp_pval',
                    is: function(s) {
                        return false;
                    },
                    format: function(text, table, cell) {
                        return parseFloat(text);
                    },
                    type: 'numeric'
                });
                $('#ewas_prot_exp_tbl').tablesorter({
                    headers: {
                        4: {
                            sorter: 'ewas_prot_exp_pval'
                        }
                    }
                });
                
                ///////// table sorter for ewas trait /////////
                $.tablesorter.addParser({
                    id: 'ewas_trait_pval',
                    is: function(s) {
                        return false;
                    },
                    format: function(text, table, cell) {
                        return parseFloat(text);
                    },
                    type: 'numeric'
                });
                $('#ewas_trait_tbl').tablesorter({
                    headers: {
                        4: {
                            sorter: 'ewas_trait_pval'
                        }
                    }
                });
                
                ///////// submit button /////////
                $('#confirm_btn').live('click', function() {
                    $("#user_input_form").submit();
                });
            });
        </script>
    </head>
    <body>
        <h2>
            Filter Result
        </h2>
        <a href="../../huwenbo/index.html">Make Another Search</a>
        <br/>
        <hr/>
"""

################################# Get User Input ###############################

# get form data
form = cgi.FieldStorage()

# get implication type and logic relation between selections
imp_types = form.getlist("imp_type")
imp_type_logic_sel = form.getvalue("imp_type_logic_sel")

max_distance = form.getvalue("max_distance")

assoc_logic_sel = form.getvalue("assoc_logic_sel")

gene_exp_pval = form.getvalue("gene_exp_pval")
protein_exp_pval = form.getvalue("protein_exp_pval")
trait_pval = form.getvalue("trait_pval")
trait_names = form.getlist("trait_names")
curated_terms = form.getlist("curated_terms")

id_type = form.getvalue("id_type")
user_genes = form.getvalue("user_genes")
user_terms = form.getvalue("user_terms")
expand_term = form.getvalue("expand_term")
search_scope = form.getvalue("search_scope")

############################## Cet Query Result ################################

# get genes from database
ewas_query_result = get_ewas_query_result(gene_exp_pval, protein_exp_pval,
    trait_pval, max_distance, trait_names, con, assoc_logic_sel)

# get user genes
gene_list = ewas_query_result[3]
if(user_genes != None):
    user_genes_list = user_genes.split()
    # conver user gene to entrez id if it's gene symbol
    if(id_type == 'GENE_SYM'):
        sym_id_map = symbol2entrez(user_genes_list)
        user_genes_list = list(sym_id_map.values())
    for gene in user_genes_list:
        gene_list.add(gene)
gene_list = list(gene_list)

# get curated terms
all_terms_list = set()
if(curated_terms != None):
    for term in curated_terms:
        all_terms_list.add(term.strip())

# get user terms
if(user_terms != None):
    user_terms_list = user_terms.split('\n')
    for term in user_terms_list:
        term = term.strip()
        all_terms_list.add(term)
all_terms_list = list(all_terms_list)

# check user search scope
if(search_scope == 'TIAB'):
    search_scope = 'Title and abstract'
else:
    search_scope = 'Full-text'

############################### Print Result ###################################

# print query summary
print """
    <h3>
        Query summary
    </h3>
"""

print '<table id="summary_tbl">'
print '<tr>'
print '<td><b>Number of genes</b></td><td>%d</td>' % len(gene_list)
print '</tr>'
print '<tr>'
print '<td><b>Number of terms</b></td><td>%d</td>' % len(all_terms_list)
print '</tr>'
print '<tr>'
print '<td><b>Search scope</b></td><td>%s</td>' % search_scope
print '</tr>'
print '</table>'
print '<br/>'
print '<button id="confirm_btn">search</button>'
print '<hr/>'

print_ewas_query_result(ewas_query_result)

################################## Hidden Form #################################

genes_form_str = ''
for i in xrange(len(gene_list)):
    genes_form_str += str(gene_list[i])
    if(i < len(gene_list)-1):
        genes_form_str += '\n'

terms_form_str =''
for i in xrange(len(all_terms_list)):
    terms_form_str += all_terms_list[i].strip()
    if(i < len(all_terms_list)-1):
            terms_form_str += '\n'

print """
        <form id="user_input_form" name="user_input" target="_blank" 
            action="./search.cgi" method="post" style="display:none">
                
            <input type="radio" id="gene_entrez" name="id_type" 
                value="entrez_id" checked />Entrez ID
                   
            <input type="radio" id="gene_sym" name="id_type" 
                value="gene_sym" />Gene symbol
            
            <textarea id="gene_txt" name="genes" 
                rows="5" cols="20" >%s</textarea>
            
            <input type="checkbox" name="expand_term" />
            
            <textarea id="terms_txt" name="terms" 
                rows="5" cols="20">%s</textarea>
            
            <input type="checkbox" name="tiab_only" checked="checked"/> 
        </form>
""" % (genes_form_str, terms_form_str)


################################### Ending #####################################

print """
    </body>
</html>
"""
con.close()
