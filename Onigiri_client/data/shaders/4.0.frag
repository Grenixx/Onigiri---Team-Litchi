#version 130

precision mediump float;

uniform float u_time;
uniform float u_trigger_time;
uniform vec2 u_resolution;
uniform vec2 u_pos;        // position monde du boss (pixels)
uniform vec2 u_camera;     // scroll caméra actuel (pixels)
uniform sampler2D u_texture;

void main() {
    float time_since_trigger = u_time - u_trigger_time;
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;

    // On convertit la position monde du boss en UV écran dynamiquement
    vec2 boss_screen = (u_pos - u_camera) / u_resolution;
    boss_screen.y = 1.0 - boss_screen.y; // flip Y

    vec2 dir = uv - boss_screen;
    dir.x *= u_resolution.x / u_resolution.y;
    float dist = length(dir);

    vec2 totalDistortion = vec2(0.0);
    float totalFlash = 0.0;

    float duration = 100.0;
    if (time_since_trigger > duration || time_since_trigger < 0.0) {
        gl_FragColor = texture2D(u_texture, uv);
        return;
    }

    for (float i = 0.0; i < 5.0; i++) {
        float waveTime = (time_since_trigger - (i * 0.15)) * 1.5; 
        if (waveTime < 0.0 || waveTime > 1.0) continue;
        
        float radius = waveTime * 1.2;
        float thickness = 0.05;
        float force = 0.03 * (1.0 - waveTime);

        float mask = pow(1.0 - abs(dist - radius), 15.0);
        mask *= step(dist, radius + thickness);
        mask *= step(radius - thickness, dist);

        totalDistortion += normalize(dir) * mask * force;
        totalFlash += mask * 0.15;
    }

    vec3 sceneColor = texture2D(u_texture, uv - totalDistortion).rgb;
    sceneColor += totalFlash;
    gl_FragColor = vec4(sceneColor, 1.0);
}