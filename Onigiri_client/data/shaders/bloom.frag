#version 330
in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform vec2 u_resolution;
uniform float u_intensity = 1.2;

void main() {
    vec2 tex_offset = 1.0 / u_resolution;
    vec4 result = vec4(0.0);
    float total_weight = 0.0;
    
    // Smooth falloff (Exponential or Gaussian-like)
    // We use a 7x7 grid for more uniformity
    for(int x = -3; x <= 3; x++) {
        for(int y = -3; y <= 3; y++) {
            float dist = length(vec2(x, y));
            // Falloff: transparency stronger at extremities (high dist = low weight)
            float weight = exp(-(dist * dist) / 5.0); 
            
            result += texture(u_texture, v_uv + vec2(x, y) * tex_offset * 1.2) * weight;
            total_weight += weight;
        }
    }

    result = (result / total_weight) * u_intensity;
    
    // Boost alpha based on brightness to make it look "thick" in the center
    float brightness = dot(result.rgb, vec3(0.299, 0.587, 0.114));
    result.a = clamp(brightness * 1.5, 0.0, 1.0);
    
    fragColor = result;
}
