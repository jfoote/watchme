function drawChart(start_date_ms, data_list){
        if (typeof $('#container').highcharts() != 'undefined') {
          $('#container').highcharts().destroy()
        }
        $('#container').highcharts({
            chart: {
                zoomType: 'x',
                spacingRight: 20
            },
            title: {
                text: 'Time spent in selected windows'
            },
            subtitle: {
                text: document.ontouchstart === undefined ?
                    'Click and drag in the plot area to zoom in' :
                    'Drag your finger over the plot to zoom in'
            },
            xAxis: {
                type: 'datetime',
                maxZoom: 14 * 24 * 3600000, // fourteen days
                title: {
                    text: null
                }
            },
            yAxis: {
                title: {
                    text: 'Minutes'
                }
            },
            tooltip: {
                shared: true
            },
            legend: {
                enabled: false
            },
            plotOptions: {
                area: {
                    fillColor: {
                        linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1},
                        stops: [
                            [0, Highcharts.getOptions().colors[0]],
                            [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
                        ]
                    },
                    lineWidth: 1,
                    marker: {
                        enabled: false
                    },
                    shadow: false,
                    states: {
                        hover: {
                            lineWidth: 1
                        }
                    },
                    threshold: null
                }
            },
    
            series: [{
                type: 'area',
                name: 'Minutes',
                pointInterval: 24 * 3600 * 1000, // 1 day * hr/day * sec/hr * ms/sec 
                pointStart: start_date_ms,
                data: data_list
            }]
        });
    }


$("#txt_name").keyup(function(event){
  document.writeln("test")
    if(event.keyCode == 13){
        $("#search_button").click();
    }
});


function searchit_simple() {
  query = document.getElementById('txt_name').value;
  // TODO: input validation!! maybe like this: window_title_tokd = JSON.stringify(item.window_title).replace(/\W/g, ' ')
  var matches = {}; // maps javascript date string to amount of time spent in matching windows on that date
  var start_date = 0; // first date in matches
  var end_date = 0; // last date in matches
  var delta = 0;
  watchme_data.forEach(function(item) {
    query.toLowerCase().split(" ").forEach(function(tok) {
      // if any search token is in the window title for this entry, add this entry to matches
      if( item.window_title.toLowerCase().search(tok) != -1) {
        jdate = new Date(item.date);
        
        // get start and end dates for this entry
        if (start_date == 0) {
          start_date = jdate;
        }
        end_date = jdate; // note: will end up being the date for the last entry that matches
        
        jdate_str = jdate.toString('yyyy-MM-dd');
        
        // cacluate time spent in window for this entry
        delta = item.end_time - item.start_time;
        
        // add time for this entry to matches
        if (jdate_str in matches) {
          matches[jdate_str] = matches[jdate_str] + delta;
        } else {
          matches[jdate_str] = delta;
        }
      }
    })
  });
  
  var values = []
  var i_str = ""
  
  // create a list of dates for HighChart
  // iterate through dates -- for each date, if we have time for date in matches, use it, otherwise set time to zero
  var i = new Date(start_date);
  while(i <= end_date) {
    i_str = i.toString('yyyy-MM-dd');
    if (i_str in matches) {
      values.push(matches[i_str]/60); // convert from seconds to minutes for display
    } else {
      values.push(0);
    }
    i.setDate(i.getDate() + 1)
  }
  
  // finally, draw the chart
  var ms = Date.UTC(start_date.getUTCFullYear(), start_date.getUTCMonth(), start_date.getUTCDate());
  drawChart(ms, values);
}
