#version 330 core

layout(location = 0) in vec3 in_pos;
layout(location = 1) in vec2 in_uv;
uniform mat4 transform;
uniform mat4 projection;

out vec2 uv;

void
main()
{
    uv = in_uv * 10;
    gl_Position = projection * transform * vec4(in_pos, 1.0);
}
