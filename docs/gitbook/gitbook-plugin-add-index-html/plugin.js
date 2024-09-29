require(['gitbook', 'jquery'], function(gitbook, $) {
    var opts;

    gitbook.events.bind('start', function(e, config) {
        opts = config['add-index-html'].elements;
    });

    gitbook.events.bind('page.change', function() {
        $.map(opts, function(ele) {
            $(ele).each((index, value) => {
                if(value.attributes.getNamedItem('href')){
                    const href = value.attributes.getNamedItem('href').value.toLowerCase()
                    
                    if( href.match(/^(?!.*png)(?!.*html)(?!.*\#)(?!.*http).*$/)){
                        value.attributes.getNamedItem('href').value += href.match(/\/$/) ? 'index.html' : '/index.html'
                    }
                    
                }
            });
        });
    });
});