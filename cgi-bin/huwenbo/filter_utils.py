from consts import *
from db_utils import *
import math

############################## CONSTANTS #######################################

# ewas user selection to table name
ewas_tbl_map = {'tbl_ewas_gene_exp': 'liver_expression_ewas',
                'tbl_ewas_prot_exp': 'liver_proteomics_ewas',
                'tbl_ewas_trait':    'clinical_metabolite_traits_ewas'}

############################# DATABASE #########################################

# create temporary tables for handling ewas database query
def handle_ewas_query(dbcon,
                 ewas_tables,
                 ewas_gene_exp_pval, 
                 ewas_prot_exp_pval,
                 ewas_trait_pval,
                 ewas_gene_exp_max_distance,
                 ewas_prot_exp_max_distance,
                 ewas_trait_max_distance,
                 ewas_trait_names,
                 ewas_assoc_logic_sel):

    # get cursor, mapping between user input and data
    cur = dbcon.cursor()
    ewas_pval_map = {'tbl_ewas_gene_exp': ewas_gene_exp_pval,
                     'tbl_ewas_prot_exp': ewas_prot_exp_pval,
                     'tbl_ewas_trait':    ewas_trait_pval}
    ewas_dist_map = {'tbl_ewas_gene_exp': ewas_gene_exp_max_distance,
                     'tbl_ewas_prot_exp': ewas_prot_exp_max_distance,
                     'tbl_ewas_trait':    ewas_trait_max_distance}
    
    # create temp tables for ewas tables
    for tbl in ewas_tables:
    
        # convert from user input to database table name
        db_table = ewas_tbl_map[tbl]
        
        # add additional constraint for searching in trait table
        ewas_trait_additional = ''
        if(db_table == 'clinical_metabolite_traits_ewas'):
            for i in xrange(len(ewas_trait_names)):
                ewas_trait_names[i] = '\''+ewas_trait_names[i]+'\''
            ewas_trait_additional += ' and phenotype in '
            ewas_trait_additional += ' (%s) ' % (','.join(ewas_trait_names))
        
        # convert numers to strings
        pval = ewas_pval_map[tbl]
        max_distance = str(ewas_dist_map[tbl])
        pval_str = str(math.pow(10.0, -1.0*float(pval)))
        
        # construct query
        query = """
                create temporary table %s_tmp as
                select * from
                    (
                        select * from %s where 
                            (
                                pval < %s
                            )
                            and 
                            (
                                dist_gene_start_methylation_site <> 'NULL'
                                and 
                                dist_gene_end_methylation_site <> 'NULL'
                            )
                            and 
                            (
                                (
                                    abs(dist_gene_start_methylation_site) < %s
                                    or
                                    abs(dist_gene_end_methylation_site) < %s 
                                )
                                or
                                (
                                    dist_gene_start_methylation_site < 0
                                    and
                                    dist_gene_end_methylation_site > 0
                                )
                            )
                            %s
                    ) as A
                    join
                    mouse_sym_human_entrez
                    on 
                    A.gene_annot_gene_sym = mouse_gene_sym
        """ % (db_table, db_table, pval_str, max_distance,
               max_distance, ewas_trait_additional)
        
        # execute query
        cur.execute(query)

    # create temp human gene id table, ewas intersection case
    if(ewas_assoc_logic_sel == 'INTERSECTION'):
    
        # create query to get intersection of human entrez ids
        sub_query = ''
        for i in xrange(len(ewas_tables)):
            tbl = ewas_tables[i]
            db_table = ewas_tbl_map[tbl]
            if(i == 0):
                sub_query = """
                    (
                        select distinct(human_entrez_id) from %s_tmp
                    )
                    as %s_tmp_id
                """ % (db_table, db_table)
            if(i > 0):
                sub_query += """
                    join
                    (
                        select distinct(human_entrez_id) from %s_tmp
                    )
                    as %s_tmp_id
                    on
                    %s_tmp_id.human_entrez_id = %s_tmp_id.human_entrez_id
                """ % (db_table,db_table,ewas_tbl_map[ewas_tables[0]],db_table)
        query = """
            create temporary table human_entrez_id_ewas_tmp as
            select distinct(%s_tmp_id.human_entrez_id) from (%s)
        """ % (ewas_tbl_map[ewas_tables[0]], sub_query)
        
        # execute query
        cur.execute(query)

    # create temp human gene id table, ewas union case
    elif(ewas_assoc_logic_sel == 'UNION'):
    
        # create query to get union of human entrez ids
        sub_query = ''
        sub_query_list = []
        for tbl in ewas_tables:
            db_table = ewas_tbl_map[tbl]
            sub_query = """
                (select distinct(human_entrez_id) from %s_tmp 
                as %s_tmp_id)
            """ % (db_table, db_table)
            sub_query_list.append(sub_query)
        query = """
            create temporary table human_entrez_id_ewas_tmp as
            select distinct(human_entrez_id) from ((%s) as A)
        """ % (' union '.join(sub_query_list))
        
        # execute query
        cur.execute(query)

# take the intersection of ewas and gwas result
def intersect_ewas_gwas_query_result(ewas_query_result,
    gwas_query_result, implications):
    
    ewas_entrez_set = ewas_query_result[len(ewas_query_result)-1]
    gwas_entrez_set = gwas_query_result[len(gwas_query_result)-1]

    # map between implication type and gene set
    imp_type_gene_set = dict()
    imp_type_gene_set['ewas_imp'] = ewas_entrez_set
    imp_type_gene_set['gwas_imp'] = gwas_entrez_set
    
    # intersect result
    final_entrez_set = set()
    implications_list = list(implications)
    if(len(implications_list) > 0):
        final_entrez_set = imp_type_gene_set[implications_list[0]]
    for i in xrange(1, len(implications_list)):
        final_entrez_set = final_entrez_set.intersection(
            imp_type_gene_set[implications_list[i]])
    
    # filter query result ewas
    ewas_gene_exp_result = filter_query_result(ewas_query_result[0],
        final_entrez_set)
    ewas_prot_exp_result = filter_query_result(ewas_query_result[1],
        final_entrez_set)
    ewas_trait_result = filter_query_result(ewas_query_result[2],
        final_entrez_set)
    
    # filter query result gwas
    gwas_gene_exp_result = filter_query_result(gwas_query_result[0],
        final_entrez_set)
    gwas_prot_exp_result = filter_query_result(gwas_query_result[1],
        final_entrez_set)
    
    combined_result = dict()
    combined_result['ewas'] = (ewas_gene_exp_result, ewas_prot_exp_result,
        ewas_trait_result, final_entrez_set)
    combined_result['gwas'] = (gwas_gene_exp_result, gwas_prot_exp_result,
        final_entrez_set)
    combined_result['gene_set'] = final_entrez_set
    
    return combined_result

# take the union of ewas and gwas result
def union_ewas_gwas_query_result(ewas_query_result, gwas_query_result):
    
    ewas_entrez_set = ewas_query_result[len(ewas_query_result)-1]
    gwas_entrez_set = gwas_query_result[len(gwas_query_result)-1]

    final_entrez_set = ewas_entrez_set.union(gwas_entrez_set)

    combined_result = dict()
    combined_result['ewas'] = ewas_query_result
    combined_result['gwas'] = gwas_query_result
    combined_result['gene_set'] = final_entrez_set
    
    return combined_result

# get ewas query result supporing information summary
def get_gwas_gene_supporting_info(gwas_query_result):
    
    gene_assoc_pos = dict()
    
    # for gene expression
    gene_exp_result = gwas_query_result[0]
    for result in gene_exp_result:
        gene_id = None
        snp_gw_pos = None
        if(len(result) == 22):
            snp_gw_pos = result[13]
            gene_id = result[21]
        elif(len(result) == 19):
            snp_gw_pos = result[10]
            gene_id = result[18]
        if(gene_id not in gene_assoc_pos):
            gene_assoc_pos[gene_id] = dict()
        if('gene_exp' not in gene_assoc_pos[gene_id]):
            gene_assoc_pos[gene_id]['gene_exp'] = set()
        gene_assoc_pos[gene_id]['gene_exp'].add(snp_gw_pos)
    
    # for protein expression
    prot_exp_result = gwas_query_result[1]
    for result in prot_exp_result:
        gene_id = result[19]
        snp_gw_pos = result[14]
        if(gene_id not in gene_assoc_pos):
            gene_assoc_pos[gene_id] = dict()
        if('prot_exp' not in gene_assoc_pos[gene_id]):
            gene_assoc_pos[gene_id]['prot_exp'] = set()
        gene_assoc_pos[gene_id]['prot_exp'].add(snp_gw_pos)
    
    return gene_assoc_pos

# get ewas query result supporing information summary
def get_ewas_gene_supporting_info(ewas_query_result):
    
    gene_assoc_pos = dict()
    
    # for gene expression
    gene_exp_result = ewas_query_result[0]
    for result in gene_exp_result:
        gene_id = result[18]
        mcg_gw_pos = result[7]
        if(gene_id not in gene_assoc_pos):
            gene_assoc_pos[gene_id] = dict()
        if('gene_exp' not in gene_assoc_pos[gene_id]):
            gene_assoc_pos[gene_id]['gene_exp'] = set()
        gene_assoc_pos[gene_id]['gene_exp'].add(mcg_gw_pos)
    
    # for protein expression
    prot_exp_result = ewas_query_result[1]
    for result in prot_exp_result:
        gene_id = result[18]
        mcg_gw_pos = result[7]
        if(gene_id not in gene_assoc_pos):
            gene_assoc_pos[gene_id] = dict()
        if('prot_exp' not in gene_assoc_pos[gene_id]):
            gene_assoc_pos[gene_id]['prot_exp'] = set()
        gene_assoc_pos[gene_id]['prot_exp'].add(mcg_gw_pos)
    
    # for trait
    trait_exp_result = ewas_query_result[2]
    for result in trait_exp_result:
        gene_id = result[20]
        mcg_gw_pos = result[6]
        if(gene_id not in gene_assoc_pos):
            gene_assoc_pos[gene_id] = dict()
        if('trait' not in gene_assoc_pos[gene_id]):
            gene_assoc_pos[gene_id]['trait'] = set()
        gene_assoc_pos[gene_id]['trait'].add(mcg_gw_pos)
    
    return gene_assoc_pos

# display ewas query result
def print_ewas_query_result(ewas_query_result):
    
    ########## gene table ##########
    print """
        <div>
            <b>Genes implicated by CG methylations associated 
            with gene expression</b>
            <button class="show_hide" type="button">hide</button>
            <br/>
            
    """
    gene_exp_result = ewas_query_result[0]
    print """
            <table id="ewas_gene_exp_tbl" class="tablesorter">
            <thead>
            <tr>
                <th>mCG genome-wide position</th>
                <th>1Mb-window</th>
                <th>Implicated mouse gene symbol</th>
                <th>Gene position</th>
                <th>p-value</th>
                <th>Human ortholog entrez ID</th>
            </tr>
            </thead>
            <tbody>"""
    for result in gene_exp_result:
        print '<tr>'
        
        # mCG 
        print '<td>%s</td>' % result[7]
        
        # mCG window
        window_st = result[6]-500000 if(result[6]-500000 > 0) else 0
        window_ed = result[6]+500000
        window_str = "chr%s:%s-%s" % (result[5], str(window_st),
            str(window_ed))
        print '<td><a target="_blank" href="%s%s">%s</a></td>' % (ucsc_url,
            window_str, window_str)
        
        # gene symbol
        print '<td>%s</td>' % result[16]
        
        # gene position
        gene_pos_str = 'chr%s:%s-%s' % (result[10], result[11], result[12])
        print '<td><a target="_blank" href="%s%s">%s</a></td>' % (ucsc_url,
            gene_pos_str, gene_pos_str)
        
        # p-value, human entrez gene id
        print '<td>%s</td><td>%s</td>' % (result[0], result[18])
        print '</tr>'
    print """
        </tbody>
        </table>
        </div>
        <hr/>"""
    
    ########## protein table ##########
    print """
        <div>
            <b>Genes implicated by CG methylations associated 
            with protein expression</b>
            <button class="show_hide" type="button">hide</button>
            <br/>
            
    """
    prot_exp_result = ewas_query_result[1]
    print """
            <table id="ewas_prot_exp_tbl" class="tablesorter">
            <thead>
            <tr>
                <th>mCG genome-wide<br/> position</th>
                <th>1Mb-window</th>
                <th>Implicated mouse<br/>gene symbol</th>
                <th>Gene position</th>
                <th>p-value</th>
                <th>Human ortholog<br/>entrez ID</th>
            </tr>
            </thead>
            <tbody>"""
    for result in prot_exp_result:
        print '<tr>'
        # mCG 
        print '<td>%s</td>' % result[7]
        
        # mCG window
        window_st = result[6]-500000 if(result[6]-500000 > 0) else 0
        window_ed = result[6]+500000
        window_str = "chr%s:%s-%s" % (result[5], str(window_st),
            str(window_ed))
        print '<td><a target="_blank" href="%s%s">%s</a></td>' % (ucsc_url,
            window_str, window_str)
        
        # gene symbol
        print '<td>%s</td>' % result[16]
        
        # gene position
        gene_pos_str = 'chr%s:%s-%s' % (result[10], result[11], result[12])
        print '<td><a target="_blank" href="%s%s">%s</a></td>' % (ucsc_url,
            gene_pos_str, gene_pos_str)
        
        # p-value, human entrez gene id
        print '<td>%s</td><td>%s</td>' % (result[0], result[18])
        print '</tr>'
    print """
        </tbody>
        </table>
        </div>
        <hr/>"""
    
    ########## trait table ##########
    print """
        <div>
            <b>Genes implicated by CG methylations associated 
            with clinical and metabolite trait</b>
            <button class="show_hide" type="button">hide</button>
            <br/>
            
    """
    trait_exp_result = ewas_query_result[2]
    print """
            <table id="ewas_trait_tbl" class="tablesorter">
            <thead>
            <tr>
                <th>mCG genome-wide<br/>position</th>
                <th>1-Mb window</th>
                <th>Implicated mouse<br/>gene symbol</th>
                <th>Gene position</th>
                <th>Phenotype</th>
                <th>Phenotype class</th>
                <th>p-value</th>
                <th>Human ortholog<br/>entrez ID</th>
            </tr>
            </thead>
            <tbody>"""
    for result in trait_exp_result:
        print '<tr>'
        
        # mCG position
        print '<td>%s</td>' % result[6]
        
        # mCG window
        window_st = result[5]-500000 if(result[5]-500000 > 0) else 0
        window_ed = result[5]+500000
        window_str = "chr%s:%s-%s" % (result[4], str(window_st),
            str(window_ed))
        print '<td><a target="_blank" href="%s%s">%s</a></td>' % (ucsc_url,
            window_str, window_str)
        
        # gene symbol
        print '<td>%s</td>' % result[16]
        
        # gene position
        gene_pos_str = 'chr%s:%s-%s' % (result[12], result[13], result[14])
        print '<td><a target="_blank" href="%s%s">%s</a></td>' % (ucsc_url,
            gene_pos_str, gene_pos_str)
        
        print '<td>%s</td><td>%s</td>' % (result[2], result[3])
        print '<td>%s</td><td>%s</td>' % (result[0], result[20])
        print '</tr>'
    print """
        </tbody>
        </table>
        </div>"""

# display ewas query result
def print_gwas_query_result(gwas_query_result):
    
    ########## gene table ##########
    print """
        <div>
            <b>Genes implicated by SNPs associated with gene expression</b>
            <button class="show_hide" type="button">hide</button>
            <br/>
            
    """
    gene_exp_result = gwas_query_result[0]
    print '<table id="gwas_gene_exp_tbl" class="tablesorter">'
    print """
            <thead>
            <tr>
                <th>SNP genome-wide position</th>
                <th>1Mb-window</th>
                <th>Implicated mouse gene symbol</th>
                <th>Gene position</th>
                <th>p-value</th>
                <th>Human ortholog entrez ID</th>
            </tr>
            </thead>
            <tbody>"""
    for result in gene_exp_result:
        print '<tr>'
        
        # SNP
        snp_pos = None
        if(len(result) == 22):
            print '<td>%s</td>' % result[13]
            snp_pos = int(result[12])
        elif(len(result) == 19):
            print '<td>%s</td>' % result[10]
            snp_pos = int(result[9])       
        
        # snp window
        window_st = snp_pos-500000 if(snp_pos-500000 > 0) else 0
        window_ed = snp_pos+500000
        window_str = ''
        if(len(result) == 22):
            window_str = "chr%s:%s-%s" % (result[11], str(window_st),
                str(window_ed))
        elif(len(result) == 19):
            window_str = "chr%s:%s-%s" % (result[8], str(window_st),
                str(window_ed))
        print '<td><a target="_blank" href="%s%s">%s</a></td>' % (ucsc_url,
            window_str, window_str)
        
        # gene symbol
        print '<td>%s</td>' % result[6]
        
        # gene position
        gene_pos_str = 'chr%s:%s-%s' % (result[1], result[2], result[3])
        print '<td><a target="_blank" href="%s%s">%s</a></td>' % (ucsc_url,
            gene_pos_str, gene_pos_str)
        
        # p-value, human entrez gene id
        if(len(result) == 22):
            print '<td>%s</td><td>%s</td>' % (result[10], result[len(result)-1])
        elif(len(result) == 19):
            print '<td>%s</td><td>%s</td>' % (result[7], result[len(result)-1])
        print '</tr>'
    print """
        </tbody>
        </table>
        </div>
        <hr/>"""
    
    ########## protein table ##########
    print """
        <div>
            <b>Genes implicated by SNPs associated with protein expression</b>
            <button class="show_hide" type="button">hide</button>
            <br/>
            
    """
    prot_exp_result = gwas_query_result[1]
    print '<table id="gwas_prot_exp_tbl" class="tablesorter">'
    print """
            <thead>
            <tr>
                <th>SNP genome-wide<br/> position</th>
                <th>1Mb-window</th>
                <th>Implicated mouse<br/>gene symbol</th>
                <th>Gene position</th>
                <th>p-value</th>
                <th>Human ortholog<br/>entrez ID</th>
            </tr>
            </thead>
            <tbody>"""
    for result in prot_exp_result:
        print '<tr>'
        # snp 
        print '<td>%s</td>' % result[14]
        
        # snp window
        snp_pos = int(result[13])
        window_st = snp_pos-500000 if(snp_pos-500000 > 0) else 0
        window_ed = snp_pos+500000
        window_str = "chr%s:%s-%s" % (result[2], str(window_st),
            str(window_ed))
        print '<td><a target="_blank" href="%s%s">%s</a></td>' % (ucsc_url,
            window_str, window_str)
        
        # gene symbol
        print '<td>%s</td>' % result[7]
        
        # gene position
        gene_pos_str = 'chr%s:%s-%s' % (result[2], result[3], result[4])
        print '<td><a target="_blank" href="%s%s">%s</a></td>' % (ucsc_url,
            gene_pos_str, gene_pos_str)
        
        # p-value, human entrez gene id
        print '<td>%s</td><td>%s</td>' % (result[11], result[len(result)-1])
        print '</tr>'
    print """
        </tbody>
        </table>
        </div>"""
