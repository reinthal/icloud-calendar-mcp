{
  pkgs,
  lib,
  config,
  inputs,
  ...
}: {
  # https://devenv.sh/basics/
  env.GREET = "devenv";

  # https://devenv.sh/packages/
  packages = [pkgs.git];

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    uv.enable = true;
    venv.enable = true;
    uv.sync.enable = true;
  };

  # https://devenv.sh/processes/
  # processes.cargo-watch.exec = "cargo-watch";

  # https://devenv.sh/services/
  # services.postgres.enable = true;

  # https://devenv.sh/scripts/
  scripts.exec-from-repo-root.exec = ''
    repo_root=$(git rev-parse --show-toplevel)
    pushd $repo_root 1>/dev/null
    eval $@
    popd 1>/dev/null
  '';
  scripts.import.exec = ''
    echo
    exec-from-repo-root python3 main.py $@
    echo
  '';

  enterShell = ''
        echo
        echo
    echo -e "\033[32m"
        echo "ICS IMPORTER INSTALLED"
        echo 'run `import <booking.ics>` to import file'
        echo
          echo -e "\033[0m"

  '';

  # https://devenv.sh/tasks/
  # tasks = {
  #   "myproj:setup".exec = "mytool build";
  #   "devenv:enterShell".after = [ "myproj:setup" ];
  # };

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
  '';

  # https://devenv.sh/git-hooks/
  # git-hooks.hooks.shellcheck.enable = true;

  # See full reference at https://devenv.sh/reference/options/
}
