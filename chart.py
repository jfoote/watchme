import string

class HtmlChart(object):
    '''
    Writes watchme chart HTML/javascript to disk
    '''
    data_def_token = "//$data_definition"
    def __init__(self, out_filepath="chart.html", template_filepath="chart_template.html"):
        '''
        POST: out_filepath is open (and FD is saved), template's preamble is 
        written to FD, and template's postlude is saved for later
        '''
        import pdb; pdb.set_trace()
        # TODO: need to fix file structure ... put watchme in $HOME
        html_template = file(template_filepath, "rt").read()
        self.out_fd = file(out_filepath, "wt")
        self.out_filepath = out_filepath
        preamble = html_template[:html_template.find(self.data_def_token)]
        self.out_fd.write(preamble)
        self.out_fd.write("var watchme_data = [ \n") # beginning of array def'n
        self.postlude = "];" # end of array def'n
        self.postlude += html_template[html_template.find(self.data_def_token)+len(self.data_def_token):]
        
    def array_append(self, item):
        #print item
        # chart.array_append([exe_name, window_title, start_time, end_time])
        self.out_fd.write("[\"%s\", \"%s\", %s, %s], \n" % tuple(item))
        
    def finish(self):
        self.out_fd.write(self.postlude)
        self.out_fd.close()
        self.out_fd = None
        
    def show(self):
        import subprocess
        # TODO: make this secure
        subprocess.Popen(self.out_filepath, shell=True)        
          
def create_chart(categories, data, out_filepath="chart.html", template_filepath="chart_template.html"):
    html_template = file(template_filepath, "rt").read()
    categories = "'" + "', '".join([c for c in categories]) + "'"
    data = ", ".join(["%d" % d for d in data])
    html = html_template.replace("$categories", categories).replace("$data", data)
    file(out_filepath, "wt").write(html)
  
if __name__ == "__main__":
    #hacky tests
    #categories = "'4/20/2013', '4/21/2013', '4/22/2013', '4/23/2013', '3/23/2013'"
    #data = "50, 100, 150, 200, 250"
    categories = ['4/20/2013', '4/21/2013', '4/22/2013', '4/23/2013', '3/23/2013']
    data = [50, 100, 150, 200, 250]
    create_chart(categories, data)
    
    # design brainstorming:
    # Loop through CSV in python
    #   create chart.html with array of all watchme data
    #   calculate "time in window" for each entry and include it
    # In chart.html javascript...
    # create lunr.js index with all watchme data
    #   an object for each entry -- search on window title
    # when user searches
    #   for each matching object
    #     keep on ongoing dict of 'categories' (dates)
    #     if this object is already in the dict, add the window-time to the value in the dict
    #       otherwise create a new entry
    #   create a new highcharts object using the keys as categories and the values as data, repsectively