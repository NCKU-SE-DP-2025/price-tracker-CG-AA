const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  configureWebpack: {
    entry: "./src/main.js",
    devServer: {
      hot: true,
    },
    watch: true,
    watchOptions: {
      ignored: /node_modules/,
      poll: 1000,
    },
  },

  // Uncomment to disable the Options API in production  

  // chainWebpack must be top-level
  chainWebpack(config) {  // Patch the existing DefinePlugin values
    config.plugin('define').tap((args) => {
      args[0]['__VUE_OPTIONS_API__'] = JSON.stringify(false)
      args[0]['__VUE_PROD_DEVTOOLS__'] = JSON.stringify(false)
      return args
    })

    // Delete this son of a very bad plugin  
    config.plugins.delete('feature-flags')
  },
})