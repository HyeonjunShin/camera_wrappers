cd /tmp
DIR_PATH="OrbbecSDK_v2.8.6_202604271452_6399409_linux_x86_64"

if [ ! -d "$DIR_PATH" ]; then
    wget https://github.com/orbbec/OrbbecSDK_v2/releases/download/v2.8.6/OrbbecSDK_v2.8.6_202604271452_6399409_linux_x86_64.tar.gz
    tar -xzf OrbbecSDK_v2.8.6_202604271452_6399409_linux_x86_64.tar.gz
    wget https://github.com/orbbec/OrbbecSDK_v2/releases/download/v2.8.6/OrbbecSDK_v2.8.6_amd64.deb
fi
cd $DIR_PATH

sudo dpkg -i OrbbecSDK_v2.8.6_amd64.deb

