#!/usr/bin/python

import math
import sqlite3 as lite
import sys

################################# DB STUFF #####################################

# connect to database
def connect_db(db_name):
    con = None
    try:
        con = lite.connect(db_name)
        con.text_factory = str
        return con
    except lite.Error, e:
        return None

############################### QUERY STUFF ####################################
        
# search database by gene symbol
def search_nhgri_gwas_catalog(con, genesym):
    if(con == None):
        return []

    c = con.cursor()
    query = """select * from nhgri_gwas_catalog 
        where Reported_Genes like '%["""+genesym+"""]%'"""
    txt = c.execute(query)
    info_list = []
    for content in txt:
        info_dict = dict()
        info_dict['author'] = content[2]
        info_dict['date'] = content[3]
        info_dict['journal'] = content[4]
        info_dict['link'] = content[5]
        info_dict['study'] = content[6]
        info_dict['trait'] = content[7]
        info_dict['region'] = content[10]
        info_dict['reported'] = content[13].replace('[','').replace(']','\n')
        info_dict['mapped'] = content[14]
        info_dict['snp_allele'] = content[20]
        info_dict['pval'] = content[27]
        info_list.append(info_dict)
    return info_list

# constrcut query for searching the gene database
def make_general_ewas_query(table_name, pval, max_distance):
    query = 'select * from %s where ' % table_name
    
    # get gene expression query
    pval_str = str(math.pow(10.0, -1.0*float(pval)))
    query += ' pval < %s and ' % pval_str
    
    # get distance to gene query
    query += ' (dist_gene_start_methylation_site <> \'NULL\' and '
    query += ' dist_gene_end_methylation_site <> \'NULL\') '
    query += ' and ( '
    # distance threshold relative to gene start gene end position
    query += ' ( '
    query += ' abs(dist_gene_start_methylation_site) < %s ' % max_distance
    query += ' or '
    query += ' abs(dist_gene_end_methylation_site) < %s ' % max_distance
    query += ' ) '
    # intragenic case
    query += ' or ( '
    query += ' dist_gene_start_methylation_site > 0 '
    query += ' and dist_gene_end_methylation_site < 0 '
    query += ' ) '
    query += ' ) '
    
    return query

# constrcut query for searching the gene database (clinical, metabolite trait)
def make_clinical_trait_ewas_query(table_name, pval, max_distance, trait_names):
        
    # add single quotes to trait names
    for i in xrange(len(trait_names)):
        trait_names[i] = '\''+trait_names[i]+'\''
    trait_names_sql_list = '('+','.join(trait_names)+')'
    
    query = make_general_ewas_query(table_name, pval, max_distance)
    query += ' and phenotype in %s ' % trait_names_sql_list
    
    return query

# construct query for mouse gene to human gene id conversion
def make_to_human_gene_id_query(from_table, from_id):
    query = 'select A.%s, B.human_entrez_id from %s' % (from_id, from_table)
    query += ' as A join mouse_mgi_human_entrez as B on '
    query += ' A.mouse_mgi_id = B.mouse_mgi_id'
    
    return query

# make query for ewas
def get_ewas_query_result(gene_exp_pval, protein_exp_pval, trait_pval,
        max_distance, trait_names, con, assoc_logic_sel):
    if(con == None):
        return ([],[],[],set())
    c = con.cursor()
    
    # get gene expression result
    gene_exp_human_entrez_set = set()
    gene_exp_result_tmp = []
    query_gene_exp = make_general_ewas_query('liver_expression_ewas',
        gene_exp_pval, max_distance)
    query = ' create temp table gene_exp_tmp as %s; ' % query_gene_exp
    query_result = c.execute(query)
    query = 'select * from gene_exp_tmp join mouse_probe_human_entrez on '
    query += ' gene_annot_gene_probe_id = mouse_probe_id;'
    query_result = c.execute(query)
    for result in query_result:
        gene_exp_result_tmp.append(result)
        gene_exp_human_entrez_set.add(result[len(result)-1])
    
    # get protein expression result
    prot_exp_human_entrez_set = set()
    prot_exp_result_tmp = []
    query_prot_exp = make_general_ewas_query('liver_proteomics_ewas',
        protein_exp_pval, max_distance)
    query = ' create temp table prot_exp_tmp as %s; ' % query_prot_exp
    query_result = c.execute(query)
    query = 'select * from prot_exp_tmp join mouse_entrez_human_entrez on '
    query += ' gene_annot_gene_entrez_id = mouse_entrez_id;'
    query_result = c.execute(query)
    for result in query_result:
       prot_exp_result_tmp.append(result)
       prot_exp_human_entrez_set.add(result[len(result)-1])
    
    # get trait expression result
    trait_exp_human_entrez_set = set()
    trait_exp_result_tmp = []
    query_trait = make_clinical_trait_ewas_query(
        'clinical_metabolite_traits_ewas', trait_pval,
        max_distance, trait_names)
    query = ' create temp table trait_tmp as %s; ' % query_trait
    query_result = c.execute(query)
    query = 'select * from trait_tmp join mouse_trans_human_entrez on '
    query += ' gene_annot_trans_id = mouse_transcript_id;'
    query_result = c.execute(query)
    for result in query_result:
        trait_exp_result_tmp.append(result)
        trait_exp_human_entrez_set.add(result[len(result)-1])
    
    # intersection or union
    final_entrez_set = set()
    if(assoc_logic_sel == 'INTERSECTION'):
        final_entrez_set = gene_exp_human_entrez_set.intersection(
            prot_exp_human_entrez_set)
        final_entrez_set = final_entrez_set.intersection(
            trait_exp_human_entrez_set)
    elif((assoc_logic_sel == 'UNION')):
        final_entrez_set = gene_exp_human_entrez_set.union(
            prot_exp_human_entrez_set)
        final_entrez_set = final_entrez_set.union(
            trait_exp_human_entrez_set)
    
    gene_exp_result = []
    for result in gene_exp_result_tmp:
        if(result[len(result)-1] in final_entrez_set):
            gene_exp_result.append(result)
    prot_exp_result = []
    for result in prot_exp_result_tmp:
        if(result[len(result)-1] in final_entrez_set):
            prot_exp_result.append(result)
    trait_exp_result = []
    for result in trait_exp_result_tmp:
        if(result[len(result)-1] in final_entrez_set):
            trait_exp_result.append(result)
    
    return (gene_exp_result, prot_exp_result, 
        trait_exp_result, final_entrez_set)

############################### DISPLAY STUFF ##################################

# print info list
def print_nhgri_gwas_info_list(info_list):
    print """
        <div>
            <b>Gene GWAS Info</b>
            <button class="show_hide" type="button">hide</button>
            <br/>
    """

    # print table header
    print '<table class="info_table">'
    print """
        <tr>
            <td class="gwas_gene">Reported Gene</td>
            <td class="gwas_title">Publication</td>
            <td class="gwas_trait">Disease/Trait</td>
            <td>Region</td>
            <td class="gwas_snp">Strongest SNP-Risk Allele</td>
            <td>P-value</td>
        </tr>
    """
    for info_dict in info_list:
        date = info_dict['date']
        link = info_dict['link']
        study = info_dict['study']
        trait = info_dict['trait']
        region = info_dict['region']
        reported = info_dict['reported']
        mapped = info_dict['mapped']
        snp_allele = info_dict['snp_allele']
        pval = info_dict['pval']
        print '<tr>'
        print '<td class="gwas_gene">%s</td>' % reported
        print '<td class="gwas_title"><a href="%s">%s</a></td>' % (link, study)
        print '<td class="gwas_trait">%s</td>' % trait
        print '<td>%s</td>' % region
        print '<td class="gwas_snp">%s</td>' % snp_allele
        print '<td>%s</td>' % pval
        print '</tr>'
    print """
        </table>
        </div>
        <br/>
    """

# search and display in one function
def nhgri_gwas_search_and_display(con, genesym):
    info_list = search_nhgri_gwas_catalog(con, genesym)
    print_nhgri_gwas_info_list(info_list)
