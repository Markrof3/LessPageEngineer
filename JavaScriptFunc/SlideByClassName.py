SLIDE_FUNC = '''
function slide(className) {
    var slider = document.getElementsByClassName(className)[document.getElementsByClassName(className).length-1];
    if(!slider){return "None"}
    var container = slider.parentNode;
    // 获取slider元素相对于视口的位置
    var rect = slider.getBoundingClientRect(),
        x0 = rect.x || rect.left,  // 水平起始位置
        y0 = rect.y || rect.top,   // 垂直起始位置
        w = container.getBoundingClientRect().width, // 容器宽度
        x1 = x0 + slide_way,               // 目标水平位置 (向右移动容器宽度的距离)
        y1 = y0;                   // 保持垂直位置不变

    // 创建并初始化 mousedown 事件
    var mousedownEvent = new MouseEvent('mousedown', {
        bubbles: true,
        cancelable: true,
        view: window,
        clientX: x0,
        clientY: y0
    });
    slider.dispatchEvent(mousedownEvent);

    // 定义分段数和总耗时
    const segments = 30; // 可根据需要调整分段数量
    const totalDuration = 500; // 总耗时1.5秒
    const segmentDuration = totalDuration / segments;

    function moveSegment(currentSegment) {
        if (currentSegment >= segments) {
            // 触发 mouseup 事件
            var mouseupEvent = new MouseEvent('mouseup', {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: x1,
                clientY: y1
            });
            slider.dispatchEvent(mouseupEvent);
            return;
        }

        // 计算当前段的新位置
        let newX = x0 + (x1 - x0) * (currentSegment / segments);
        let newY = y0 + (y1 - y0) * (currentSegment / segments);

        // 添加随机偏移
        const randomOffsetX = (Math.random() - 0.5) * 10; // ±10像素的随机偏移
        const randomOffsetY = (Math.random() - 0.5) * 10;
        newX += randomOffsetX;
        newY += randomOffsetY;

        // 创建并初始化 mousemove 事件
        var mousemoveEvent = new MouseEvent('mousemove', {
            bubbles: true,
            cancelable: true,
            view: window,
            clientX: newX,
            clientY: newY
        });
        slider.dispatchEvent(mousemoveEvent);

        // 使用 requestAnimationFrame 和 setTimeout 结合来保证平滑过渡
        setTimeout(() => moveSegment(currentSegment + 1),  segmentDuration + Math.random() * 10);
    }

    // 开始分段移动
    moveSegment(0);
}
slide('id_value')
'''