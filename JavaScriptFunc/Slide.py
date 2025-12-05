SLIDE_FUNC = '''
function initiateSlide(id) {
    // 定义将要在Worker中运行的函数
    function slide(time) {
        self.onmessage = function(e) {
            if (e.data.action === 'start') {
                actualSlide(e.data.x_0, e.data.y_0, e.data.id, time);
            }
        };

        function actualSlide(x_0, y_0, id, duration) {
            const x0 = x_0; // 示例起始位置
            const y0 = y_0;
            const x1 = x0 + slide_way;
            const y1 = y0;

            const segments = 20;
            const totalDuration = duration || 800;
            const segmentDuration = totalDuration / segments;

            function moveSegment(currentSegment) {
                if (currentSegment >= segments) {
                    self.postMessage({action: 'complete'});
                    return;
                }

                const newX = x0 + (x1 - x0) * (currentSegment / segments);
                const newY = y0 + (y1 - y0) * (currentSegment / segments);

                const randomOffsetX = (Math.random() - 0.5) * 10;
                const randomOffsetY = (Math.random() - 0.5) * 10;
                const finalX = newX + randomOffsetX;
                const finalY = newY + randomOffsetY;

                self.postMessage({
                    action: 'moveSegment',
                    id: id,
                    eventType: 'mousemove',
                    clientX: finalX,
                    clientY: finalY
                });

                setTimeout(() => moveSegment(currentSegment + 1), segmentDuration);
            }

            moveSegment(0);
        }
    }

    // 将函数转换为字符串并创建一个Blob
    const blob = new Blob(['(' + slide.toString() + ')(' + 400 + ')'], {type: 'application/javascript'});
    
    // 创建一个指向Blob的URL
    const workerScript = window.URL.createObjectURL(blob);
    
    // 创建一个新的Worker
    const worker = new Worker(workerScript);

    // 监听来自Worker的消息
    worker.onmessage = function(e) {
        const data = e.data;
        if (data.action === 'moveSegment') {
            const mouseEvent = new MouseEvent("mousemove", {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: data.clientX,
                clientY: data.clientY
            });
            window.slider.dispatchEvent(mouseEvent);
        } else if (data.action === 'complete') {
                        const mouseEvent = new MouseEvent("mouseup", {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: data.clientX,
                clientY: data.clientY
            });
            window.slider.dispatchEvent(mouseEvent);

        }
    };

    // 发送消息给Worker开始滑动
    worker.postMessage({x_0:window.x0, y_0:window.y0, action: 'start', id: id});
}

// 调用initiateSlide函数
slider = window.document.getElementById("id_value");
    rect = slider.getBoundingClientRect(),
        x0 = rect.x || rect.left,  // 水平起始位置
        y0 = rect.y || rect.top,   // 垂直起始位置
    mousedownEvent = new MouseEvent('mousedown', {
        bubbles: true,
        cancelable: true,
        view: window,
        clientX: x0,
        clientY: y0
});
slider.dispatchEvent(mousedownEvent);
initiateSlide("id_value");
'''
