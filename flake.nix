{
  description = "swos-scout: read-only scouting report for OpenSWOS career saves";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {
    self,
    nixpkgs,
  }: let
    systems = ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"];
    forAll = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
  in {
    packages = forAll (pkgs: {
      default = pkgs.writers.writePython3Bin "swos-scout" {
        flakeIgnore = ["E501" "W503"];
        # writePython3Bin writes its own shebang.
      } (nixpkgs.lib.removePrefix "#!/usr/bin/env python3\n" (builtins.readFile ./swos-scout.py));
    });
    apps = forAll (pkgs: {
      default = {
        type = "app";
        program = "${self.packages.${pkgs.stdenv.hostPlatform.system}.default}/bin/swos-scout";
      };
    });
  };
}
