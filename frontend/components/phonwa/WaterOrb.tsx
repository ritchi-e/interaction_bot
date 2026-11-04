"use client";

import { useEffect, useRef } from "react";

/**
 * Interactive liquid orb — Phonwa purple/ink theme, round silhouette, white backlight.
 */
export function WaterOrb({ className = "" }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;

    const gl = canvas.getContext("webgl", { alpha: true, antialias: true, premultipliedAlpha: false });
    if (!gl) return;

    const vs = `
      attribute vec2 a;
      void main(){ gl_Position = vec4(a,0.,1.); }
    `;

    const fs = `
      precision highp float;
      uniform vec2 u_res;
      uniform float u_time;
      uniform vec2 u_mouse;
      uniform float u_hover;

      float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }
      float noise(vec2 p){
        vec2 i = floor(p); vec2 f = fract(p);
        float a = hash(i); float b = hash(i+vec2(1.,0.));
        float c = hash(i+vec2(0.,1.)); float d = hash(i+vec2(1.,1.));
        vec2 u = f*f*(3.-2.*f);
        return mix(a,b,u.x) + (c-a)*u.y*(1.-u.x) + (d-b)*u.x*u.y;
      }
      float fbm(vec2 p){
        float v=0.; float a=.5;
        for(int i=0;i<5;i++){ v+=a*noise(p); p*=2.05; a*=.5; }
        return v;
      }

      void main(){
        vec2 uv = (gl_FragCoord.xy - .5*u_res) / min(u_res.x, u_res.y);
        vec2 m = (u_mouse - .5*u_res) / min(u_res.x, u_res.y);

        float t = u_time * .35;
        float r = length(uv);

        // Keep silhouette perfectly round; only warp interior color
        float radius = 0.46;
        float mask = smoothstep(radius + 0.006, radius - 0.01, r);

        float n = fbm(uv*3.2 + vec2(t*.6, -t*.4));
        float n2 = fbm(uv*5.5 - vec2(t*.3, t*.55));
        float warp = (n-.5)*.055 + (n2-.5)*.028;

        float md = length(uv - m);
        float ripple = sin(md*26. - u_time*6.) * exp(-md*4.8) * u_hover * .038;
        vec2 duv = uv + normalize(uv+1e-4)*warp*mask + (uv-m)*ripple*2.0*mask;

        // Phonwa theme: ink depth → violet → soft lilac
        float marble = fbm(duv*4.2 + n*1.3);
        float veins = smoothstep(.32, .78, fbm(duv*6.5 + marble));
        vec3 cDeep = vec3(0.055, 0.075, 0.09);       // ink
        vec3 cMid  = vec3(0.35, 0.28, 0.62);         // deep violet
        vec3 cLite = vec3(0.79, 0.71, 1.0);          // lilac (#C9B6FF)
        vec3 cHi   = vec3(0.96, 0.94, 0.98);         // bone highlight
        vec3 col = mix(cDeep, cMid, marble);
        col = mix(col, cLite, veins * 0.55);
        col = mix(col, cHi, pow(marble, 2.2) * 0.22);

        vec3 N = normalize(vec3(duv, sqrt(max(.001, radius*radius - r*r))));
        vec3 L = normalize(vec3(-.25 + m.x*.45, .5 + m.y*.35, 1.0));
        float diff = clamp(dot(N,L), 0., 1.);
        float spec = pow(clamp(dot(reflect(-L,N), vec3(0.,0.,1.)), 0., 1.), 56.);
        float fres = pow(1. - clamp(N.z, 0., 1.), 2.4);

        col = col * (.32 + .78*diff) + cHi*spec*.9 + cLite*fres*.28;

        float sheen = smoothstep(.22, 0., abs(dot(normalize(duv+1e-4), normalize(m+1e-4)) - .12 - sin(u_time)*.04));
        col += cHi * sheen * u_hover * .2 * mask;

        // Soft white rim light on the orb itself
        col += vec3(1.0) * fres * .18 * mask;

        // Thin white rim light just behind the sphere edge (line-thick)
        float halo = exp(-pow((r - radius) / .018, 2.0));
        float backlight = halo * (0.7 + 0.25 * u_hover);
        vec3 glowCol = vec3(1.0, 1.0, 0.98);

        vec3 outc = glowCol * backlight;
        outc = mix(outc, col, mask);
        float alpha = max(mask, backlight * 0.95);
        alpha *= smoothstep(1.0, .42, length(uv));

        gl_FragColor = vec4(outc, alpha);
      }
    `;

    function compile(type: number, src: string) {
      const s = gl!.createShader(type)!;
      gl!.shaderSource(s, src);
      gl!.compileShader(s);
      if (!gl!.getShaderParameter(s, gl!.COMPILE_STATUS)) {
        console.error(gl!.getShaderInfoLog(s));
      }
      return s;
    }

    const prog = gl.createProgram()!;
    gl.attachShader(prog, compile(gl.VERTEX_SHADER, vs));
    gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(prog);
    gl.useProgram(prog);

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "a");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    const uRes = gl.getUniformLocation(prog, "u_res");
    const uTime = gl.getUniformLocation(prog, "u_time");
    const uMouse = gl.getUniformLocation(prog, "u_mouse");
    const uHover = gl.getUniformLocation(prog, "u_hover");

    let raf = 0;
    let running = true;
    const mouse = { x: 0, y: 0, tx: 0, ty: 0, hover: 0, th: 0 };
    const start = performance.now();

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = wrap!.getBoundingClientRect();
      const w = Math.max(1, Math.floor(rect.width * dpr));
      const h = Math.max(1, Math.floor(rect.height * dpr));
      if (canvas!.width !== w || canvas!.height !== h) {
        canvas!.width = w;
        canvas!.height = h;
      }
      gl!.viewport(0, 0, w, h);
    }

    function onMove(e: PointerEvent) {
      const rect = canvas!.getBoundingClientRect();
      const dpr = canvas!.width / rect.width;
      mouse.tx = (e.clientX - rect.left) * dpr;
      mouse.ty = (rect.height - (e.clientY - rect.top)) * dpr;
      mouse.th = 1;
    }
    function onLeave() {
      mouse.th = 0;
    }

    wrap.addEventListener("pointermove", onMove);
    wrap.addEventListener("pointerenter", onMove);
    wrap.addEventListener("pointerleave", onLeave);

    const ro = new ResizeObserver(resize);
    ro.observe(wrap);
    resize();
    mouse.x = mouse.tx = canvas.width * 0.5;
    mouse.y = mouse.ty = canvas.height * 0.5;

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    function frame(now: number) {
      if (!running) return;
      resize();
      mouse.x += (mouse.tx - mouse.x) * 0.12;
      mouse.y += (mouse.ty - mouse.y) * 0.12;
      mouse.hover += (mouse.th - mouse.hover) * 0.08;

      gl!.clearColor(0, 0, 0, 0);
      gl!.clear(gl!.COLOR_BUFFER_BIT);
      gl!.uniform2f(uRes, canvas!.width, canvas!.height);
      gl!.uniform1f(uTime, (now - start) / 1000);
      gl!.uniform2f(uMouse, mouse.x, mouse.y);
      gl!.uniform1f(uHover, mouse.hover);
      gl!.drawArrays(gl!.TRIANGLE_STRIP, 0, 4);
      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      ro.disconnect();
      wrap.removeEventListener("pointermove", onMove);
      wrap.removeEventListener("pointerenter", onMove);
      wrap.removeEventListener("pointerleave", onLeave);
      gl.getExtension("WEBGL_lose_context")?.loseContext();
    };
  }, []);

  return (
    <div ref={wrapRef} className={`water-orb ${className}`.trim()} aria-hidden="true">
      <div className="water-orb-spotlight" />
      <canvas ref={canvasRef} className="water-orb-canvas" />
    </div>
  );
}
