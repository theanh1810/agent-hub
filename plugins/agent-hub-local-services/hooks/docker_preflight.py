#!/usr/bin/env python3
"""PreToolUse(Bash) hook: block a duplicate backing-service container or a non-127.0.0.1 publish.
Exit 2 = block (stderr goes to Claude), 0 = allow. The shared-service rules need the infra_dir option
(CLAUDE_PLUGIN_OPTION_INFRA_DIR); unset, only the publish rules (127.0.0.1, publish-all, host network) fire.
Docker CLI missing: exit 0 silently."""
import json, os, shlex, shutil, subprocess, sys

if shutil.which("docker") is None:
    sys.exit(0)
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    _fn = getattr(_stream, "reconfigure", None)
    if _fn:
        try:
            _fn(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass
try:
    data = json.loads(sys.stdin.read() or "{}")
    cmd = (data.get("tool_input") or {}).get("command") or ""
    cwd0 = data.get("cwd")
    cwd0 = cwd0 if isinstance(cwd0, str) and cwd0 else os.getcwd()
except Exception:
    sys.exit(0)
if not isinstance(cmd, str) or "docker" not in cmd:
    sys.exit(0)

SHARED = {"postgres": {"shared-postgres"}, "redis": {"shared-redis"}, "mailpit": {"shared-mailpit"},
          "seaweedfs": {"shared-s3"}, "minio": set()}
ALL_SHARED = set().union(*SHARED.values())
_infra = os.environ.get("CLAUDE_PLUGIN_OPTION_INFRA_DIR", "").strip()
INFRA = os.path.abspath(os.path.expanduser(_infra)) if _infra else None
POINTER = os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "refs", "local-services.md")
SEPS = set(";&|()")
ALIAS = {"postgresql": "postgres", "postgis": "postgres", "redis-stack": "redis", "redis-stack-server": "redis"}
RUN_VAL = {"--name", "-p", "--publish", "-v", "--volume", "-e", "--env", "--network", "--net", "-w", "--workdir",
           "-u", "--user", "--entrypoint", "-l", "--label", "--restart", "-m", "--memory", "--env-file", "-h",
           "--hostname", "--mount", "--add-host", "--cap-add", "--cap-drop", "--device", "--platform", "--pull",
           "--cpus", "--ip", "--expose", "--link", "--dns", "--log-driver", "--log-opt", "--shm-size", "--tmpfs",
           "--volumes-from", "--group-add", "--health-cmd", "--health-interval", "--ulimit", "--security-opt",
           "--cidfile", "--stop-signal", "--stop-timeout", "--runtime", "--gpus", "--pid", "--ipc", "--cgroupns",
           "-a", "-c", "--add-host", "--annotation", "--attach", "--blkio-weight", "--blkio-weight-device",
           "--cgroup-parent", "--cpu-period", "--cpu-quota", "--cpu-rt-period", "--cpu-rt-runtime", "--cpu-shares",
           "--cpuset-cpus", "--cpuset-mems", "--detach-keys", "--device-cgroup-rule", "--device-read-bps",
           "--device-read-iops", "--device-write-bps", "--device-write-iops", "--dns-option", "--dns-search",
           "--domainname", "--health-retries", "--health-start-interval", "--health-start-period",
           "--health-timeout", "--ip6", "--isolation", "--kernel-memory", "--label-file", "--link-local-ip",
           "--mac-address", "--memory-reservation", "--memory-swap", "--memory-swappiness", "--network-alias",
           "--oom-score-adj", "--pids-limit", "--storage-opt", "--sysctl", "--ulimit", "--userns", "--uts",
           "--volume-driver"}  # every value-taking flag of `docker run --help` (Docker 2026-10-30) plus --net
RUN_BOOL = {"--detach", "--disable-content-trust", "--help", "--init", "--interactive", "--no-healthcheck",
            "--oom-kill-disable", "--privileged", "--quiet", "--read-only", "--rm", "--sig-proxy", "--tty",
            "--use-api-socket"}
SHORT_BOOL, SHORT_VAL = set("ditq"), set("pvewulmhac")
HOST_NET = "host networking exposes every container port on all host interfaces"
PUBLISH_ALL = "publish-all binds every exposed port on 0.0.0.0"
COMPOSE_VAL = {"-f", "--file", "-p", "--project-name", "--project-directory", "--profile", "--env-file",
               "--ansi", "--parallel", "--progress"}


class Unknown(Exception):
    pass


def segments(text):
    lex = shlex.shlex(text, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    toks = list(lex)  # ValueError on unbalanced quotes
    segs, cur = [], []
    for t in toks:
        if t and set(t) <= SEPS:
            segs.append(cur); cur = []
        else:
            cur.append(t)
    segs.append(cur)
    return [s for s in segs if s]


def kind_of(image):
    if INFRA is None:
        return None  # shared-service rules are off without infra_dir
    base = image.split("@")[0].rsplit("/", 1)[-1].split(":")[0].lower()
    base = ALIAS.get(base, base)
    return base if base in SHARED else None


def opt_value(tok):
    return tok.split("=", 1)[1] if "=" in tok else None


def publish_bad(val):
    return not val.startswith("127.0.0.1:")


def run_decision(args):
    name, image, pubs, i, host, pall = None, None, [], 0, False, False
    while i < len(args):
        a = args[i]
        if a.startswith("--") and "=" in a:
            k, v = a.split("=", 1)
            if k == "--name": name = v
            elif k == "--publish": pubs.append(v)
            elif k in ("--network", "--net") and v == "host": host = True
        elif a in RUN_VAL:
            v = args[i + 1] if i + 1 < len(args) else ""
            if a == "--name": name = v
            elif a in ("-p", "--publish"): pubs.append(v)
            elif a in ("--network", "--net") and v == "host": host = True
            i += 1
        elif a == "--publish-all":
            pall = True
        elif a.startswith("--"):
            if a not in RUN_BOOL:
                raise Unknown("unknown flag %s" % a)
        elif a.startswith("-") and len(a) > 1:
            letters = a[1:]
            for j, c in enumerate(letters):
                if c == "P":
                    pall = True
                elif c in SHORT_BOOL:
                    continue
                elif c in SHORT_VAL:
                    attached = letters[j + 1:]
                    if not attached:
                        attached = args[i + 1] if i + 1 < len(args) else ""
                        i += 1
                    if c == "p": pubs.append(attached)
                    break
                else:
                    break
        else:
            image = a
            break
        i += 1
    if image:
        k = kind_of(image)
        if k and name not in SHARED[k]:
            return "a second %s container (%s) is not allowed" % (k, name or "unnamed")
    if host:
        return HOST_NET
    if pall:
        return PUBLISH_ALL
    for p in pubs:
        if publish_bad(p):
            return "port publish %s is not bound to 127.0.0.1" % p
    return None


def compose_files(args):
    files, pdir, verb, i = [], None, None, 0
    while i < len(args):
        a = args[i]
        if a in COMPOSE_VAL:
            v = args[i + 1] if i + 1 < len(args) else ""
            if a in ("-f", "--file"): files.append(v)
            elif a == "--project-directory": pdir = v
            i += 2
            continue
        if a.startswith("--") and "=" in a:
            k, v = a.split("=", 1)
            if k == "--file": files.append(v)
            elif k == "--project-directory": pdir = v
        elif a.startswith("-"):
            pass
        else:
            verb = a
            break
        i += 1
    return files, pdir, verb


def allowed_path(p):
    p = os.path.abspath(p)
    return (INFRA is not None and (p == INFRA or p.startswith(INFRA + os.sep))) or "/deploy/" in p + "/"


def expand(p, cwd):
    p = os.path.expandvars(os.path.expanduser(p))
    if not os.path.isabs(p):
        if cwd is None:
            raise Unknown("working directory unknown after cd")
        p = os.path.join(cwd, p)
    return os.path.normpath(p)


def compose_decision(args, cwd):
    files, pdir, verb = compose_files(args)
    if verb not in ("up", "create", "run", "start"):
        return None
    files = [expand(f, cwd) for f in files]
    base = expand(pdir, cwd) if pdir else cwd
    if not files:
        if base is None:
            raise Unknown("working directory unknown after cd")
        base = os.path.abspath(base)
        if allowed_path(base):
            return None
        for n in ("compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml"):
            if os.path.isfile(os.path.join(base, n)):
                files = [os.path.join(base, n)]
                break
        if not files:
            raise Unknown("no compose file found")
    if all(allowed_path(f) for f in files):
        return None
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
    try:
        import yaml
    except Exception:
        raise Unknown("PyYAML missing")
    for f in files:
        if allowed_path(f):
            continue
        try:
            doc = yaml.safe_load(open(f)) or {}
        except Exception as e:
            raise Unknown("cannot read %s" % f)
        for svc, d in (doc.get("services") or {}).items():
            d = d or {}
            k = kind_of(str(d.get("image") or ""))
            if k and d.get("container_name") not in SHARED[k]:
                return "compose service %s defines its own %s" % (svc, k)
            if d.get("network_mode") == "host":
                return HOST_NET
            for p in d.get("ports") or []:
                if isinstance(p, dict):
                    bad = str(p.get("host_ip")) != "127.0.0.1"
                else:
                    bad = publish_bad(str(p))
                if bad:
                    return "compose service %s publishes %s not bound to 127.0.0.1" % (svc, p)
    return None


def start_decision(args):
    if INFRA is None:
        return None
    for n in [a for a in args if not a.startswith("-")]:
        if n in ALL_SHARED:
            continue
        try:
            r = subprocess.run(["docker", "inspect", "--format", "{{.Config.Image}}", n],
                               capture_output=True, text=True, timeout=5)
        except Exception:
            raise Unknown("docker inspect unavailable")
        if r.returncode != 0:
            raise Unknown("docker inspect %s failed" % n)
        k = kind_of(r.stdout.strip())
        if k:
            return "container %s is another %s; start the shared one" % (n, k)
    return None


def next_cwd(seg, cwd):
    """The directory after a `cd`-like segment; unchanged for any other segment; None = unknown."""
    if not seg or seg[0] in ("pushd", "popd"):
        return None if seg else cwd
    if seg[0] != "cd":
        return cwd
    args = seg[1:]
    if not args or args == ["~"]:
        return os.path.expanduser("~")
    if len(args) != 1 or args[0] == "-":
        return None
    d = os.path.expandvars(os.path.expanduser(args[0]))
    if "$" in d or "`" in d:
        return None
    if not os.path.isabs(d):
        if cwd is None:
            return None
        d = os.path.join(cwd, d)
    return os.path.normpath(d)


def decide(seg, cwd):
    toks = list(seg)
    while toks and "=" in toks[0] and not toks[0].startswith("-"):
        toks.pop(0)
    if toks and toks[0] == "rtk":
        toks.pop(0)
    if toks and toks[0] == "sudo":
        toks.pop(0)
        while toks and toks[0].startswith("-"):
            toks = toks[2:] if toks[0] in ("-u", "-g") else toks[1:]
    if not toks:
        return None
    exe = os.path.basename(toks[0])
    if exe == "docker-compose":
        return compose_decision(toks[1:], cwd)
    if exe != "docker":
        return None
    rest, i = toks[1:], 0
    while i < len(rest) and rest[i].startswith("-"):
        i += 2 if rest[i] in ("-H", "--host", "-c", "--context", "--config", "-l", "--log-level") else 1
    rest = rest[i:]
    if not rest:
        return None
    if rest[0] == "container":
        rest = rest[1:]
        if not rest:
            return None
    sub, args = rest[0], rest[1:]
    if sub in ("run", "create"):
        return run_decision(args)
    if sub == "compose":
        return compose_decision(args, cwd)
    if sub in ("start", "restart"):
        return start_decision(args)
    return None


if os.environ.get("CLAUDE_DOCKER_PREFLIGHT") == "off":
    sys.exit(0)
try:
    segs = segments(cmd)
except ValueError as e:
    print("docker-preflight: could not parse (%s); allowed" % e, file=sys.stderr)
    sys.exit(0)
for s in segs:
    for t in s:
        if t == "CLAUDE_DOCKER_PREFLIGHT=off":
            sys.exit(0)
        if "=" not in t or t.startswith("-"):
            break
unknown = None
cwd = cwd0
for s in segs:
    try:
        reason = decide(s, cwd)
    except Unknown as e:
        unknown = unknown or str(e)
        reason = None
    cwd = next_cwd(s, cwd)
    if reason:
        print("docker-preflight: %s; use the shared service (%s)" % (reason, POINTER), file=sys.stderr)
        sys.exit(2)
if unknown:
    print("docker-preflight: could not parse (%s); allowed" % unknown, file=sys.stderr)
sys.exit(0)