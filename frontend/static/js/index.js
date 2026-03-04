var tick = 0;
var imgData = null;

// let lastTime = 0;
//
// function gameLoop(currentTime) {
//     // 1. Calculate Delta Time (time passed since last frame)
//     const deltaTime = currentTime - lastTime;
//     lastTime = currentTime;
//
//     // 2. Update Simulation Logic (The "Tick")
//     update(deltaTime);
//
//     // 3. Render the Canvas
//     render();
//
//     // 4. Queue the next frame
//     requestAnimationFrame(gameLoop);
// }
//
// function update(dt) {
//     // This is where you calculate car positions, 
//     // check sensors, and run your traffic logic.
// }
//
// function render() {
//     // This is where you call ctx.putImageData(imageData, 0, 0)
// }
//
// // Kick off the loop
// requestAnimationFrame(gameLoop);

function update() {
    setTimeout(function() {
        tick++;
        updateImageData(data);
        requestAnimationFrame(draw);
    });
}

function start() {
    var canvas = document.getElementById('canvas')
    var width = canvas.width
    var height = canvas.height
    var ctx = canvas.getContext('2d');

    const imageData = ctx.createImageData(width, height);
    const data = imageData.data; // This is the pixel array

    // Loop through every pixel
    for (let i = 0; i < data.length; i += 4) {
        data[i] = 44;  // Red (0-255)
        data[i + 1] = 62;  // Green
        data[i + 2] = 80;  // Blue
        data[i + 3] = 255; // Alpha (Opacity)
    }

    function draw() {
        console.log(`Updating canvas... ${tick}`);
        const data = imageData.data; // This is the pixel array
        for (let i = 0; i < data.length; i += 4) {
            data[i] = (data[i] + 1) % 256; // Change Red channel
        }

        ctx.putImageData(imageData, 0, 0);
        setTimeout(function() {
            tick++;
            requestAnimationFrame(draw);
        }, 1000);
    }

    ctx.putImageData(imageData, 0, 0);
    setTimeout(function() {
        tick++;
        requestAnimationFrame(draw);
    }, 1000);
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded and parsed');
    start();
});
