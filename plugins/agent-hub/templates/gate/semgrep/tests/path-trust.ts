import * as fs from "fs";
import * as path from "path";
import { readFileSync } from "fs";
import { readFile } from "fs/promises";
import { readFile as rf, rename, writeFile } from "fs/promises";
import { writeFileSync } from "node:fs";
import { readdir } from "node:fs/promises";
import { format } from "util";

const BASE = path.resolve("data");

export function flaggedArgv(): string {
  const name = process.argv[2];
  // ruleid: agent-hub-path-trust-js
  return fs.readFileSync(path.join(BASE, name), "utf8");
}

export function flaggedBody(req: { body: { file: string } }): void {
  const target = path.join(BASE, req.body.file);
  // ruleid: agent-hub-path-trust-js
  fs.writeFileSync(target, "x");
}

export function cleanResolved(req: { query: { file: string } }): string {
  const target = path.resolve(BASE, req.query.file);
  if (!target.startsWith(BASE + path.sep)) {
    throw new Error("outside base");
  }
  // ok: agent-hub-path-trust-js
  return fs.readFileSync(target, "utf8");
}

export function flaggedNamedImport(req: { query: { file: string } }): Buffer {
  // ruleid: agent-hub-path-trust-js
  return readFileSync(req.query.file);
}

export async function flaggedPromisesImport(req: { params: { file: string } }): Promise<Buffer> {
  // ruleid: agent-hub-path-trust-js
  return readFile(req.params.file);
}

export function flaggedCopyTarget(req: { body: { dest: string } }): void {
  // ruleid: agent-hub-path-trust-js
  fs.copyFileSync(path.join(BASE, "a.json"), req.body.dest);
}

export function cleanDataArgument(req: { body: { content: string } }): void {
  // ok: agent-hub-path-trust-js
  fs.writeFileSync(path.join(BASE, "out.json"), req.body.content);
}

export async function cleanPromisesResolved(req: { params: { file: string } }): Promise<Buffer> {
  const target = path.resolve(BASE, req.params.file);
  if (!target.startsWith(BASE + path.sep)) {
    throw new Error("outside base");
  }
  // ok: agent-hub-path-trust-js
  fs.copyFileSync(path.join(BASE, "a.json"), target);
  // ok: agent-hub-path-trust-js
  return readFile(target);
}

export function flaggedNodeSpecifier(req: { query: { file: string } }): void {
  // ruleid: agent-hub-path-trust-js
  writeFileSync(req.query.file, "x");
}

export async function flaggedNodePromisesSpecifier(req: { query: { dir: string } }): Promise<string[]> {
  // ruleid: agent-hub-path-trust-js
  return readdir(req.query.dir);
}

export async function flaggedAliasedImport(req: { query: { file: string } }): Promise<Buffer> {
  // ruleid: agent-hub-path-trust-js
  return rf(req.query.file);
}

export async function flaggedNamedRenameTarget(req: { body: { dest: string } }): Promise<void> {
  // ruleid: agent-hub-path-trust-js
  await rename(path.join(BASE, "a"), req.body.dest);
}

export async function cleanNamedDataArgument(req: { body: { content: string } }): Promise<void> {
  // ok: agent-hub-path-trust-js
  await writeFile(path.join(BASE, "out.json"), req.body.content);
}

export function cleanOtherModuleImport(req: { query: { file: string } }): string {
  // ok: agent-hub-path-trust-js
  return format(req.query.file);
}
