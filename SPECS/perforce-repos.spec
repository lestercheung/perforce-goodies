Name: perforce-repos
Version: 0.1
Release: 1%{?dist}
Summary: Perforce package repositories
License: MIT
URL: https://www.perforce.com/perforce-packages
BuildArch: noarch

Source0: perforce.repo
Source1: perforce-el8.repo

%description
This package provides the package repository files for Perforce.

%install
install -d -m 0755 %{buildroot}%{_sysconfdir}/yum.repos.d
install -p -m 644 %{_sourcedir}/*.repo %{buildroot}%{_sysconfdir}/yum.repos.d/


%package -n perforce-repo
Summary: Perforce package repository

%description -n perforce-repo
This package provides the package repository files for Perforce.

%files -n perforce-repo
%config(noreplace) %{_sysconfdir}/yum.repos.d/perforce.repo


%package -n perforce-el8-repo
Summary: Perforce package (EL8)

%description -n perforce-el8-repo
This package provides the package repository files for Perforce.

%files -n perforce-el8-repo
%config(noreplace) %{_sysconfdir}/yum.repos.d/perforce-el8.repo


%changelog
* Sun Jul 11 2021 Lester Cheung <lestercheung@users.noreply.github.com>
- First cut
