sudo cp /Users/jiawei/workspace/github/tomato/bin/jiawei.tomato.plist /Library/LaunchDaemons/jiawei.tomato.plist
launchctl unload /Library/LaunchDaemons/jiawei.tomato.plist
launchctl load /Library/LaunchDaemons/jiawei.tomato.plist
launchctl list jiawei.github.tomato
