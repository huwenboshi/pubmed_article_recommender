from consts import *
from db_utils import *

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
    gene_exp_result = ewas_query_result[0]
    print '<h3>Genes implicated by CG methylations '
    print 'associated with gene expression</h3>'
    print '<table id="ewas_gene_exp_tbl" class="tablesorter">'
    print """
            <thead>
            <tr>
                <th>mCG genome-wide position</th>
                <th>1Mb-window</th>
                <th>Implicated mouse gene probe ID</th>
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
        
        # probe ID
        print '<td>%s</td>' % result[15]
        
        # gene position
        gene_pos_str = 'chr%s:%s-%s' % (result[10], result[11], result[12])
        print '<td><a target="_blank" href="%s%s">%s</a></td>' % (ucsc_url,
            gene_pos_str, gene_pos_str)
        
        # p-value, human entrez gene id
        print '<td>%s</td><td>%s</td>' % (result[0], result[18])
        print '</tr>'
    print """
        </tbody>
        </table>"""
    
    print '<br/>'
    print '<hr/>'
    
    ########## protein table ##########
    prot_exp_result = ewas_query_result[1]
    print '<h3>Genes implicated by CG methylations associated '
    print 'with protein expression</h3>'
    print '<table id="ewas_prot_exp_tbl" class="tablesorter">'
    print """
            <thead>
            <tr>
                <th>mCG genome-wide<br/> position</th>
                <th>1Mb-window</th>
                <th>Implicated mouse<br/>gene entrez ID</th>
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
        
        # entrez id
        print '<td>%s</td>' % result[15]
        
        # gene position
        gene_pos_str = 'chr%s:%s-%s' % (result[10], result[11], result[12])
        print '<td><a target="_blank" href="%s%s">%s</a></td>' % (ucsc_url,
            gene_pos_str, gene_pos_str)
        
        # p-value, human entrez gene id
        print '<td>%s</td><td>%s</td>' % (result[0], result[18])
        print '</tr>'
    print """
        </tbody>
        </table>"""
    
    print '<br/>'
    print '<hr/>'
    
    ########## trait table ##########
    trait_exp_result = ewas_query_result[2]
    print '<h3>Genes implicated by CG methylations associated '
    print 'with clinical and metabolite trait</h3>'
    print '<table id="ewas_trait_tbl" class="tablesorter">'
    print """
            <thead>
            <tr>
                <th>mCG genome-wide<br/>position</th>
                <th>1-Mb window</th>
                <th>Implicated mouse<br/>gene transcript ID</th>
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
        
        # transcript id
        print '<td>%s</td>' % result[17]
        
        # gene position
        gene_pos_str = 'chr%s:%s-%s' % (result[12], result[13], result[14])
        print '<td><a target="_blank" href="%s%s">%s</a></td>' % (ucsc_url,
            gene_pos_str, gene_pos_str)
        
        print '<td>%s</td><td>%s</td>' % (result[2], result[3])
        print '<td>%s</td><td>%s</td>' % (result[0], result[20])
        print '</tr>'
    print """
        </tbody>
        </table>"""
