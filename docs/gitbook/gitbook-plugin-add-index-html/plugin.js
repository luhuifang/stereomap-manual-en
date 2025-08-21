require(['gitbook', 'jquery'], function(gitbook, $) {
    var opts;

    gitbook.events.bind('start', function(e, config) {
        opts = config['add-index-html'].elements;
    });

    gitbook.events.bind('page.change', function() {
        $.map(opts, function(ele) {
            $(ele).each((index, value) => {
                const attr = value.attributes.getNamedItem('href');
                if(attr){
                    const href = attr.value.toLowerCase()
                    // console.log(href)
                    
                    if( href.match(/^(?!.*png)(?!.*html)(?!.*\#)(?!.*http).*$/)){
                        attr.value += href.match(/\/$/) ? 'index.html' : '/index.html'
                    } else if(href.match(/^(?!#).*$/) && href.match(/^.*\#.*$/) && href.match(/^(?!.*html\#).*$/)){

                        //如果链接是bgipan.geomics.cn，则不做替换
                        if(href.indexOf('bgipan.genomics.cn') !== -1){
                            return;
                        }

                        // 优化判断：如果包含"/#"，则替换"/#"为"/index.html#"，否则替换第一个"#"为"/index.html#"
                        if(href.indexOf('/#') !== -1){
                            attr.value = href.replace('#', 'index.html#');
                        } else {
                            attr.value = href.replace('#', '/index.html#');
                        }
                    }
                }
            });
        });
    });
});