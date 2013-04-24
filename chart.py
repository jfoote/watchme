import string

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